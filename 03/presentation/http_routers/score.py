"""HTTP роутер для метода online_score."""

from typing import Any, Dict, Tuple

from domain.requests.score import OnlineScoreArguments
from domain.requests.base import MethodRequestModel
from domain.utils import get_validation_errors
from presentation.http.schemas.codes import INVALID_REQUEST, OK
from pydantic import ValidationError
from scoring import get_score

def handle_online_score(
    request: MethodRequestModel, ctx: Dict[str, Any]
) -> Tuple[Dict[str, Any], int]:
    """Обработчик метода online_score."""
    arguments = request.arguments or {}
    try:
        score_args = OnlineScoreArguments(**arguments)
    except ValidationError as e:
        return {"error": get_validation_errors(e)}, INVALID_REQUEST

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
