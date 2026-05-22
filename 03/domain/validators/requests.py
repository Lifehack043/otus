"""Pydantic-модели запросов."""

from typing import Any, List, Optional, Tuple

from pydantic import BaseModel

from domain.validators.birthday import validate_birthday
from domain.validators.char import validate_char
from domain.validators.client_ids import validate_client_ids
from domain.validators.date import validate_date
from domain.validators.email import validate_email
from domain.validators.gender import validate_gender
from domain.validators.phone import validate_phone


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

        if self.phone is not None and self.phone != "":
            err = validate_phone(self.phone)
            if err:
                errors.append(err)

        if self.email is not None and self.email != "":
            err = validate_email(self.email)
            if err:
                errors.append(err)

        if self.first_name is not None and self.first_name != "":
            err = validate_char("first_name", self.first_name)
            if err:
                errors.append(err)

        if self.last_name is not None and self.last_name != "":
            err = validate_char("last_name", self.last_name)
            if err:
                errors.append(err)

        if self.birthday is not None and self.birthday != "":
            err = validate_birthday(self.birthday)
            if err:
                errors.append(err)

        if self.gender is not None and self.gender != "":
            err = validate_gender(self.gender)
            if err:
                errors.append(err)

        return errors

    def validate_pairs(self) -> List[str]:
        """Проверяет наличие хотя бы одной валидной пары."""
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

        if self.client_ids is None:
            errors.append("Поле 'client_ids' обязательно")
        else:
            err = validate_client_ids(self.client_ids)
            if err:
                errors.append(err)

        if self.date is not None and self.date != "":
            err = validate_date(self.date)
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
        return self.login == "admin"

    def validate(self) -> List[str]:
        errors = []

        if self.account is not None and self.account != "":
            if not isinstance(self.account, str):
                errors.append("Поле 'account' должно быть строкой")

        if self.login is None:
            errors.append("Поле 'login' обязательно")
        elif self.login != "" and not isinstance(self.login, str):
            errors.append("Поле 'login' должно быть строкой")

        if self.token is None:
            errors.append("Поле 'token' обязательно")
        elif self.token != "" and not isinstance(self.token, str):
            errors.append("Поле 'token' должно быть строкой")

        if self.method is None:
            errors.append("Поле 'method' обязательно")
        elif not isinstance(self.method, str):
            errors.append("Поле 'method' должно быть строкой")
        elif self.method == "":
            errors.append("Поле 'method' не может быть пустым")

        if self.arguments is None:
            errors.append("Поле 'arguments' обязательно")
        elif not isinstance(self.arguments, dict):
            errors.append("Поле 'arguments' должно быть словарем")

        return errors
