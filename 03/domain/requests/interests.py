"""Pydantic-модель запроса для метода clients_interests."""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from domain.validators.client_ids import validate_client_ids
from domain.validators.date import validate_date


class ClientsInterestsArguments(BaseModel, extra="ignore"):
    """Аргументы метода clients_interests."""
    model_config = ConfigDict(validate_default=True)

    client_ids: Optional[Any] = None
    date: Optional[str] = None

    @field_validator("client_ids", mode="before")
    @classmethod
    def validate_client_ids_field(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("Поле 'client_ids' обязательно")
        error = validate_client_ids(value)
        if error:
            raise ValueError(error)
        return value

    @field_validator("date")
    @classmethod
    def validate_date_field(cls, value: Any) -> Any:
        error = validate_date(value)
        if error:
            raise ValueError(error)
        return value
