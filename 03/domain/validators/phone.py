"""Валидатор поля phone."""

from typing import Any, Optional


def validate_phone(value: Any) -> Optional[str]:
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
