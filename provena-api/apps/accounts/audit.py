import functools
import logging

logger = logging.getLogger(__name__)


def audit_action(action: str, target_type: str = "", get_target_id=None):
    """
    Decorator for DRF APIView methods (post/patch/delete).
    Records a row in AuditLog after a successful (2xx) response.

    Usage:
        @audit_action("supplier.approved", target_type="Supplier", get_target_id=lambda req, kwargs: kwargs.get("pk"))
        def post(self, request, pk):
            ...
    """

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(self, request, *args, **kwargs):
            response = fn(self, request, *args, **kwargs)
            if response is not None and 200 <= response.status_code < 300:
                try:
                    from apps.accounts.models import AuditLog

                    target_id = ""
                    if get_target_id is not None:
                        try:
                            target_id = str(get_target_id(request, kwargs))
                        except Exception:  # noqa: S110  # nosec B110
                            pass

                    AuditLog.objects.create(
                        actor=request.user if request.user.is_authenticated else None,
                        action=action,
                        target_type=target_type,
                        target_id=target_id,
                        metadata={},
                    )
                except Exception:
                    logger.exception("audit_action failed for %s", action)
            return response

        return wrapper

    return decorator
