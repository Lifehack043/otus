"""Утилиты для работы с Pydantic."""

from pydantic import ValidationError


def get_validation_errors(exc: ValidationError) -> str:
    """Извлекает сообщения об ошибках из ValidationError."""
    messages = []
    for error in exc.errors():
        msg = error.get("msg", "")
        if msg and msg not in messages:
            messages.append(msg)
    return "; ".join(messages)
