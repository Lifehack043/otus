"""Валидатор поля date."""

import datetime
from typing import Any, Optional


def validate_date(value: Any) -> Optional[str]:
    """date - строка в формате DD.MM.YYYY."""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        return "Поле 'date' должно быть строкой"
    try:
        datetime.datetime.strptime(value, "%d.%m.%Y")
    except ValueError:
        return "Поле 'date' должно быть в формате DD.MM.YYYY"
    return None
