"""Валидатор поля client_ids."""

from typing import Any, Optional


def validate_client_ids(value: Any) -> Optional[str]:
    """client_ids - массив чисел, не пустой."""
    if not isinstance(value, list):
        return "Поле 'client_ids' должно быть массивом"
    if len(value) == 0:
        return "Поле 'client_ids' не должно быть пустым"
    for item in value:
        if not isinstance(item, int):
            return "Поле 'client_ids' должно содержать только числа"
    return None
