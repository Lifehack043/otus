"""Валидатор поля birthday."""

import datetime
from typing import Any, Optional


def validate_birthday(value: Any) -> Optional[str]:
    """birthday - дата DD.MM.YYYY, с которой прошло не больше 70 лет."""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        return "Поле 'birthday' должно быть строкой"
    try:
        birth_date = datetime.datetime.strptime(value, "%d.%m.%Y")
        now = datetime.datetime.now()
        years_passed = (now - birth_date).days / 365.25
        if years_passed > 70:
            return "Поле 'birthday': с указанной даты прошло больше 70 лет"
    except ValueError:
        return "Поле 'birthday' должно быть в формате DD.MM.YYYY"
    return None
