"""HTTP роутер для метода clients_interests."""

from typing import Any, Dict, Tuple

from domain.validators.requests import ClientsInterestsArguments, MethodRequestModel
from presentation.http.schemas.codes import INVALID_REQUEST, OK
from scoring import get_interests


def handle_clients_interests(
    request: MethodRequestModel, ctx: Dict[str, Any]
) -> Tuple[Dict[str, Any], int]:
    """Обработчик метода clients_interests."""
    arguments = request.arguments or {}
    interests_args = ClientsInterestsArguments(**arguments)
    errors = interests_args.validate()

    if errors:
        return {"error": "; ".join(errors)}, INVALID_REQUEST

    client_ids = interests_args.client_ids
    ctx["nclients"] = len(client_ids)

    result = {}
    for cid in client_ids:
        result[str(cid)] = get_interests(cid)

    return result, OK
