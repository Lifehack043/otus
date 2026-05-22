"""HTTP роутер для метода online_score."""

from typing import Any, Dict, Tuple

from domain.validators.requests import MethodRequestModel, OnlineScoreArguments
from presentation.http.schemas.codes import INVALID_REQUEST, OK
from scoring import get_score


def handle_online_score(
    request: MethodRequestModel, ctx: Dict[str, Any]
) -> Tuple[Dict[str, Any], int]:
    """Обработчик метода online_score."""
    arguments = request.arguments or {}
    score_args = OnlineScoreArguments(**arguments)
    errors = score_args.validate()

    if errors:
        return {"error": "; ".join(errors)}, INVALID_REQUEST

    # Контекст
    ctx["has"] = score_args.get_has_fields()

    # Админ всегда получает 42
    if request.is_admin:
        return {"score": 42}, OK

    # Вычисляем скор
    phone_val = score_args.phone
    if isinstance(phone_val, (int, float)):
        phone_val = str(int(phone_val))

    score = get_score(
        phone=phone_val or None,
        email=score_args.email or None,
        birthday=score_args.birthday or None,
        gender=score_args.gender or None,
        first_name=score_args.first_name or None,
        last_name=score_args.last_name or None,
    )
    return {"score": score}, OK
