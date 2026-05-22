"""HTTP error messages and schemas."""

from enum import Enum

from presentation.http.schemas.codes import (
    BAD_REQUEST,
    FORBIDDEN,
    INTERNAL_ERROR,
    INVALID_REQUEST,
    NOT_FOUND,
)


class ErrorMessage(Enum):
    """Enum with standard HTTP error messages."""
    BAD_REQUEST = "Bad Request"
    FORBIDDEN = "Forbidden"
    NOT_FOUND = "Not Found"
    INVALID_REQUEST = "Invalid Request"
    INTERNAL_ERROR = "Internal Server Error"


ERRORS = {
    BAD_REQUEST: ErrorMessage.BAD_REQUEST.value,
    FORBIDDEN: ErrorMessage.FORBIDDEN.value,
    NOT_FOUND: ErrorMessage.NOT_FOUND.value,
    INVALID_REQUEST: ErrorMessage.INVALID_REQUEST.value,
    INTERNAL_ERROR: ErrorMessage.INTERNAL_ERROR.value,
}
