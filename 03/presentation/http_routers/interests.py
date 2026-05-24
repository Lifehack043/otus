"""HTTP роутер для метода clients_interests."""

from typing import Any, Dict, Tuple

from domain.requests.interests import ClientsInterestsArguments
from domain.requests.base import MethodRequestModel
from domain.utils import get_validation_errors
from presentation.http.schemas.codes import INVALID_REQUEST, OK
from pydantic import ValidationError
from scoring import get_interests

def handle_clients_interests(
    request: MethodRequestModel, ctx: Dict[str, Any]
) -> Tuple[Dict[str, Any], int]:
    """Обработчик метода clients_interests."""
    arguments = request.arguments or {}
    try:
        interests_args = ClientsInterestsArguments(**arguments)
    except ValidationError as e:
        return {"error": get_validation_errors(e)}, INVALID_REQUEST

    client_ids = interests_args.client_ids
    ctx["nclients"] = len(client_ids)

    result = {}
    for cid in client_ids:
        result[str(cid)] = get_interests(cid)

    return result, OK
