import datetime
import hashlib
import json
import logging
import sys
import uuid
from argparse import ArgumentParser
from email.message import Message
from enum import Enum
from http.server import (
    BaseHTTPRequestHandler,
    HTTPServer,
)
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, field_validator, model_validator
from scoring import get_interests, get_score


class Gender(Enum):
    UNKNOWN = 0
    MALE = 1
    FEMALE = 2


class ErrorMessage(Enum):
    BAD_REQUEST = "Bad Request"
    FORBIDDEN = "Forbidden"
    NOT_FOUND = "Not Found"
    INVALID_REQUEST = "Invalid Request"
    INTERNAL_ERROR = "Internal Server Error"


SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"

OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500

ERRORS = {
    BAD_REQUEST: ErrorMessage.BAD_REQUEST.value,
    FORBIDDEN: ErrorMessage.FORBIDDEN.value,
    NOT_FOUND: ErrorMessage.NOT_FOUND.value,
    INVALID_REQUEST: ErrorMessage.INVALID_REQUEST.value,
    INTERNAL_ERROR: ErrorMessage.INTERNAL_ERROR.value,
}


# ─────────────────────────────────────────────
# Pydantic-модели валидации
# ─────────────────────────────────────────────

def _validate_phone(value: Any) -> Optional[str]:
    """phone - строка или число, длиной 11, начинается с 7."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        value_str = str(int(value))
    elif isinstance(value, str):
        value_str = value
    else:
        return "Поле 'phone' должно быть строкой или числом"
    if len(value_str) != 11:
        return "Поле 'phone' должно быть длиной 11 символов"
    if not value_str.startswith("7"):
        return "Поле 'phone' должно начинаться с 7"
    return None


def _validate_email(value: Any) -> Optional[str]:
    """email - строка, в которой есть @."""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        return "Поле 'email' должно быть строкой"
    if "@" not in value:
        return "Поле 'email' должно содержать @"
    return None


def _validate_date(value: Any) -> Optional[str]:
    """date - строка в формате DD.MM.YYYY."""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        return "Поле 'date' должно быть строкой"
    try:
        datetime.datetime.strptime(value, "%d.%m.%Y")
    except ValueError:
        return "Поле 'date' должно быть в формате DD.MM.YYYY"
    return None


def _validate_birthday(value: Any) -> Optional[str]:
    """birthday - дата DD.MM.YYYY, с которой прошло не больше 70 лет."""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        return "Поле 'birthday' должно быть строкой"
    try:
        birth_date = datetime.datetime.strptime(value, "%d.%m.%Y")
        now = datetime.datetime.now()
        years_passed = (now - birth_date).days / 365.25
        if years_passed > 70:
            return "Поле 'birthday': с указанной даты прошло больше 70 лет"
    except ValueError:
        return "Поле 'birthday' должно быть в формате DD.MM.YYYY"
    return None


def _validate_gender(value: Any) -> Optional[str]:
    """gender - число 0, 1 или 2."""
    if value is None or value == "":
        return None
    if not isinstance(value, int):
        return "Поле 'gender' должно быть числом (0, 1 или 2)"
    if value not in (0, 1, 2):
        return "Поле 'gender' должно быть 0, 1 или 2"
    return None


def _validate_char(value: Any) -> Optional[str]:
    """Проверяет, что значение — строка (если не None/пустое)."""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        return f"Поле должно быть строкой"
    return None


def _validate_client_ids(value: Any) -> Optional[str]:
    """client_ids - массив чисел, не пустой."""
    if not isinstance(value, list):
        return "Поле 'client_ids' должно быть массивом"
    if len(value) == 0:
        return "Поле 'client_ids' не должно быть пустым"
    for item in value:
        if not isinstance(item, int):
            return "Поле 'client_ids' должно содержать только числа"
    return None


class OnlineScoreArguments(BaseModel, extra="ignore"):
    """Аргументы метода online_score."""
    phone: Optional[Any] = None
    email: Optional[Any] = None
    first_name: Optional[Any] = None
    last_name: Optional[Any] = None
    birthday: Optional[Any] = None
    gender: Optional[Any] = None

    def validate_fields(self) -> List[str]:
        """Валидирует каждое поле и возвращает список ошибок."""
        errors = []

        # phone
        if self.phone is not None and self.phone != "":
            err = _validate_phone(self.phone)
            if err:
                errors.append(err)

        # email
        if self.email is not None and self.email != "":
            err = _validate_email(self.email)
            if err:
                errors.append(err)

        # first_name
        if self.first_name is not None and self.first_name != "":
            err = _validate_char(self.first_name)
            if err:
                errors.append(f"Поле 'first_name' должно быть строкой")

        # last_name
        if self.last_name is not None and self.last_name != "":
            err = _validate_char(self.last_name)
            if err:
                errors.append(f"Поле 'last_name' должно быть строкой")

        # birthday
        if self.birthday is not None and self.birthday != "":
            err = _validate_birthday(self.birthday)
            if err:
                errors.append(err)

        # gender
        if self.gender is not None and self.gender != "":
            err = _validate_gender(self.gender)
            if err:
                errors.append(err)

        return errors

    def validate_pairs(self) -> List[str]:
        """Проверяет наличие хотя бы одной валидной пары."""
        # Считаем поле «присутствующим», если оно есть в model_fields_set
        # и не пустое.
        def is_filled(field_name: str) -> bool:
            val = getattr(self, field_name)
            return val is not None and val != ""

        has_phone = is_filled("phone")
        has_email = is_filled("email")
        has_first_name = is_filled("first_name")
        has_last_name = is_filled("last_name")
        has_gender = is_filled("gender")
        has_birthday = is_filled("birthday")

        has_phone_email = has_phone and has_email
        has_name = has_first_name and has_last_name
        has_gender_birthday = has_gender and has_birthday

        if not (has_phone_email or has_name or has_gender_birthday):
            return ["Необходимо указать хотя бы одну пару: phone+email, first_name+last_name, gender+birthday"]
        return []

    def get_has_fields(self) -> List[str]:
        """Возвращает список полей, которые были не пустые."""
        result = []
        for field_name in ["phone", "email", "first_name", "last_name", "birthday", "gender"]:
            val = getattr(self, field_name)
            if val is not None and val != "":
                result.append(field_name)
        return result

    def validate(self) -> List[str]:
        """Полная валидация: поля + пары."""
        errors = self.validate_fields()
        if errors:
            return errors
        return self.validate_pairs()


class ClientsInterestsArguments(BaseModel, extra="ignore"):
    """Аргументы метода clients_interests."""
    client_ids: Optional[Any] = None
    date: Optional[Any] = None

    def validate(self) -> List[str]:
        errors = []

        # client_ids обязателен
        if self.client_ids is None:
            errors.append("Поле 'client_ids' обязательно")
        else:
            err = _validate_client_ids(self.client_ids)
            if err:
                errors.append(err)

        # date опционален
        if self.date is not None and self.date != "":
            err = _validate_date(self.date)
            if err:
                errors.append(err)

        return errors


class MethodRequestModel(BaseModel, extra="ignore"):
    """Базовая модель запроса к /method."""
    account: Optional[Any] = None
    login: Optional[Any] = None
    method: Optional[Any] = None
    token: Optional[Any] = None
    arguments: Optional[Any] = None

    @property
    def is_admin(self) -> bool:
        return self.login == ADMIN_LOGIN

    def validate(self) -> List[str]:
        errors = []

        # account - опционально, строка
        if self.account is not None and self.account != "":
            if not isinstance(self.account, str):
                errors.append("Поле 'account' должно быть строкой")

        # login - обязательно, строка, может быть пустым
        if self.login is None:
            errors.append("Поле 'login' обязательно")
        elif self.login != "" and not isinstance(self.login, str):
            errors.append("Поле 'login' должно быть строкой")

        # token - обязательно, строка, может быть пустым
        if self.token is None:
            errors.append("Поле 'token' обязательно")
        elif self.token != "" and not isinstance(self.token, str):
            errors.append("Поле 'token' должно быть строкой")

        # method - обязательно, строка, НЕ может быть пустым
        if self.method is None:
            errors.append("Поле 'method' обязательно")
        elif not isinstance(self.method, str):
            errors.append("Поле 'method' должно быть строкой")
        elif self.method == "":
            errors.append("Поле 'method' не может быть пустым")

        # arguments - обязательно, словарь, может быть пустым
        if self.arguments is None:
            errors.append("Поле 'arguments' обязательно")
        elif not isinstance(self.arguments, dict):
            errors.append("Поле 'arguments' должно быть словарем")

        return errors


def check_auth(request: MethodRequestModel) -> bool:
    account = request.account or ""
    login = request.login or ""
    token = request.token or ""

    if request.is_admin:
        digest = hashlib.sha512(
            (datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode("utf-8")
        ).hexdigest()
    else:
        digest = hashlib.sha512(
            (account + login + SALT).encode("utf-8")
        ).hexdigest()
    return digest == token


def handle_online_score(request: MethodRequestModel, ctx: dict) -> Tuple[dict, int]:
    """Обработчик метода online_score."""
    arguments = request.arguments or {}
    score_args = OnlineScoreArguments(**arguments)
    errors = score_args.validate()

    if errors:
        return {"error": "; ".join(errors)}, INVALID_REQUEST

    # Контекст
    ctx["has"] = score_args.get_has_fields()

    # Админ всегда получает 42
    if request.is_admin:
        return {"score": 42}, OK

    # Вычисляем скор
    phone_val = score_args.phone
    if isinstance(phone_val, (int, float)):
        phone_val = str(int(phone_val))

    score = get_score(
        phone=phone_val or None,
        email=score_args.email or None,
        birthday=score_args.birthday or None,
        gender=score_args.gender or None,
        first_name=score_args.first_name or None,
        last_name=score_args.last_name or None,
    )
    return {"score": score}, OK


def handle_clients_interests(request: MethodRequestModel, ctx: dict) -> Tuple[dict, int]:
    """Обработчик метода clients_interests."""
    arguments = request.arguments or {}
    interests_args = ClientsInterestsArguments(**arguments)
    errors = interests_args.validate()

    if errors:
        return {"error": "; ".join(errors)}, INVALID_REQUEST

    client_ids = interests_args.client_ids
    ctx["nclients"] = len(client_ids)

    result = {}
    for cid in client_ids:
        result[str(cid)] = get_interests(cid)

    return result, OK


METHOD_HANDLERS = {
    "online_score": handle_online_score,
    "clients_interests": handle_clients_interests,
}


def method_handler(
    request: dict[str, Any],
    ctx: dict[str, Any],
    settings: dict[str, Any] = None,
) -> tuple[dict[str, Any], int]:
    """Основной обработчик метода /method."""
    body = request.get("body", {})
    settings = settings or {}

    # Валидируем базовый запрос
    method_request = MethodRequestModel(**body)
    errors = method_request.validate()
    if errors:
        return {"error": "; ".join(errors)}, INVALID_REQUEST

    # Проверяем аутентификацию
    if not check_auth(method_request):
        return {}, FORBIDDEN

    # Получаем имя метода
    method_name = method_request.method
    if method_name not in METHOD_HANDLERS:
        return {"error": f"Метод '{method_name}' не найден"}, NOT_FOUND

    # Вызываем обработчик метода
    handler = METHOD_HANDLERS[method_name]
    response, code = handler(method_request, ctx)

    return response, code


class MainHTTPHandler(BaseHTTPRequestHandler):
    router: dict[str, Callable] = {"method": method_handler}

    def get_request_id(self, headers: Message) -> str:
        return headers.get("HTTP_X_REQUEST_ID", uuid.uuid4().hex)

    def do_POST(self) -> None:
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers["Content-Length"]))
            request = json.loads(data_string)
        except Exception:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path](
                        {"body": request, "headers": self.headers},
                        context,
                    )
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            error_msg = response if response and isinstance(response, str) else ERRORS.get(code, "Unknown Error")
            r = {"error": error_msg, "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode("utf-8"))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", action="store", type=int, default=8080)
    parser.add_argument("-l", "--log", action="store", default=None)
    args = parser.parse_args()

    log_config = {
        "level": logging.INFO,
        "format": "[%(asctime)s] %(levelname).1s %(message)s",
        "datefmt": "%Y.%m.%d %H:%M:%S",
    }

    if args.log:
        log_config["filename"] = args.log
    else:
        log_config["stream"] = sys.stdout

    logging.basicConfig(**log_config)

    server = HTTPServer(("localhost", args.port), MainHTTPHandler)

    logging.info("Starting server at %s" % args.port)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

    server.server_close()
