import datetime
import json
import logging
import uuid
from argparse import ArgumentParser
from email.message import Message
from http.server import (
    BaseHTTPRequestHandler,
    HTTPServer,
)
from typing import Any, Callable, Dict, Tuple

import config
from domain.services.auth import ADMIN_LOGIN, ADMIN_SALT, SALT, check_auth
from domain.requests.base import MethodRequestModel
from domain.utils import get_validation_errors
from presentation.http_routers.interests import handle_clients_interests
from presentation.http_routers.score import handle_online_score
from presentation.http.schemas.codes import (
    BAD_REQUEST,
    FORBIDDEN,
    INTERNAL_ERROR,
    INVALID_REQUEST,
    NOT_FOUND,
    OK,
)
from presentation.http.schemas.errors import ERRORS
from pydantic import ValidationError

METHOD_HANDLERS = {
    "online_score": handle_online_score,
    "clients_interests": handle_clients_interests,
}

def method_handler(
    request: Dict[str, Any],
    ctx: Dict[str, Any],
    settings: Dict[str, Any] = None,
) -> Tuple[Dict[str, Any], int]:
    """Основной обработчик метода /method."""
    body = request.get("body", {})
    settings = settings or {}

    # Валидируем базовый запрос
    try:
        method_request = MethodRequestModel(**body)
    except ValidationError as e:
        return {"error": get_validation_errors(e)}, INVALID_REQUEST

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
    router: Dict[str, Callable] = {"method": method_handler}

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
            error_msg = (
                response if response and isinstance(response, str)
                else ERRORS.get(code, "Unknown Error")
            )
            r = {"error": error_msg, "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode("utf-8"))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-p", "--port", action="store", type=int, default=config.DEFAULT_PORT
    )
    parser.add_argument("-l", "--log", action="store", default=None)
    args = parser.parse_args()

    logging.basicConfig(**config.get_log_config(args.log))

    server = HTTPServer((config.DEFAULT_HOST, args.port), MainHTTPHandler)

    logging.info("Starting server at %s" % args.port)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

    server.server_close()
