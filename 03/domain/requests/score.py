"""Pydantic-модель запроса для метода online_score."""

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from domain.validators.birthday import validate_birthday
from domain.validators.char import validate_char
from domain.validators.email import validate_email
from domain.validators.gender import validate_gender
from domain.validators.phone import validate_phone


class OnlineScoreArguments(BaseModel, extra="ignore"):
    """Аргументы метода online_score."""
    model_config = ConfigDict(validate_default=True)

    phone: Optional[Any] = None
    email: Optional[Any] = None
    first_name: Optional[Any] = None
    last_name: Optional[Any] = None
    birthday: Optional[Any] = None
    gender: Optional[Any] = None

    @field_validator("phone")
    @classmethod
    def validate_phone_field(cls, value: Any) -> Any:
        error = validate_phone(value)
        if error:
            raise ValueError(error)
        return value

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, value: Any) -> Any:
        error = validate_email(value)
        if error:
            raise ValueError(error)
        return value

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, value: Any) -> Any:
        error = validate_char("first_name", value)
        if error:
            raise ValueError(error)
        return value

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, value: Any) -> Any:
        error = validate_char("last_name", value)
        if error:
            raise ValueError(error)
        return value

    @field_validator("birthday")
    @classmethod
    def validate_birthday_field(cls, value: Any) -> Any:
        error = validate_birthday(value)
        if error:
            raise ValueError(error)
        return value

    @field_validator("gender")
    @classmethod
    def validate_gender_field(cls, value: Any) -> Any:
        error = validate_gender(value)
        if error:
            raise ValueError(error)
        return value

    @model_validator(mode="after")
    def validate_pairs(self) -> "OnlineScoreArguments":
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
            raise ValueError(
                "Необходимо указать хотя бы одну пару: "
                "phone+email, first_name+last_name, gender+birthday"
            )
        return self

    def get_has_fields(self) -> List[str]:
        """Возвращает список полей, которые были не пустые."""
        result = []
        for field_name in ["phone", "email", "first_name", "last_name", "birthday", "gender"]:
            val = getattr(self, field_name)
            if val is not None and val != "":
                result.append(field_name)
        return result
