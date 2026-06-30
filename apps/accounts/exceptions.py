import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

_STATUS_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
}


def provena_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled exception in %s", context.get("view"))
        return None

    data = response.data

    if isinstance(data, dict) and "detail" in data:
        response.data = {
            "error": {
                "code": _STATUS_CODES.get(response.status_code, "ERROR"),
                "message": str(data["detail"]),
            }
        }
    elif isinstance(data, dict) and "error" not in data:
        response.data = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed.",
                "fields": data,
            }
        }

    return response
