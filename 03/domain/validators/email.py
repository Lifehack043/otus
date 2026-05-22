"""Валидатор поля email."""

from typing import Any, Optional


def validate_email(value: Any) -> Optional[str]:
    """email - строка, в которой есть @."""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        return "Поле 'email' должно быть строкой"
    if "@" not in value:
        return "Поле 'email' должно содержать @"
    return None
