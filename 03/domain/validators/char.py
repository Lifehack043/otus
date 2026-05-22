"""Валидатор строковых полей (char)."""

from typing import Any, Optional


def validate_char(field_name: str, value: Any) -> Optional[str]:
    """Проверяет, что значение — строка (если не None/пустое)."""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        return f"Поле '{field_name}' должно быть строкой"
    return None
