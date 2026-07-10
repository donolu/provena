from django.db import connection
from django.http import HttpRequest, JsonResponse


def health_check(request: HttpRequest) -> JsonResponse:
    """Readiness probe: confirms the process is up and the database is reachable.

    Reachable through Nginx at /api/v1/health/. Used by the E2E workflow to wait
    for the stack before running tests, and suitable for load-balancer probes.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "error", "database": "down"}, status=503)
    return JsonResponse({"status": "ok"})
