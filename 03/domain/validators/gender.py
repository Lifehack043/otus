"""Валидатор поля gender."""

from typing import Any, Optional


def validate_gender(value: Any) -> Optional[str]:
    """gender - число 0, 1 или 2."""
    if value is None or value == "":
        return None
    if not isinstance(value, int):
        return "Поле 'gender' должно быть числом (0, 1 или 2)"
    if value not in (0, 1, 2):
        return "Поле 'gender' должно быть 0, 1 или 2"
    return None
