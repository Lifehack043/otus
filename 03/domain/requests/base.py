"""Pydantic-модель базового запроса к /method."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class MethodRequestModel(BaseModel, extra="ignore"):
    """Базовая модель запроса к /method."""
    model_config = ConfigDict(validate_default=True)

    account: Optional[str] = None
    login: Optional[str] = None
    method: Optional[str] = None
    token: Optional[str] = None
    arguments: Optional[Dict[Any, Any]] = None

    @property
    def is_admin(self) -> bool:
        return self.login == "admin"

    @field_validator("method", mode="before")
    @classmethod
    def validate_method(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("Поле 'method' обязательно")
        if not isinstance(value, str):
            raise ValueError("Поле 'method' должно быть строкой")
        if value == "":
            raise ValueError("Поле 'method' не может быть пустым")
        return value

    @field_validator("arguments", mode="before")
    @classmethod
    def validate_arguments(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("Поле 'arguments' обязательно")
        if not isinstance(value, dict):
            raise ValueError("Поле 'arguments' должно быть словарем")
        return value
