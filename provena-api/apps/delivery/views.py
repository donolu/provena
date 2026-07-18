from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services


@extend_schema(tags=["Delivery"])
class CourierWebhookView(APIView):
    # Courier webhook — no session auth. A real provider adapter must verify a signature header
    # before trusting the payload (deferred with the real adapter, ADR-013).
    authentication_classes: list = []
    permission_classes: list = []

    @extend_schema(
        summary="Courier status webhook",
        request=None,
        responses={200: OpenApiResponse(description="Acknowledged")},
    )
    def post(self, request: Request) -> Response:
        services.handle_status_event(request.data)
        return Response({"ok": True})


@extend_schema(tags=["Delivery (Admin)"])
class AdminCourierReconciliationView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Platform delivery reconciliation summary",
        responses={
            200: OpenApiResponse(description="Fee vs courier-cost totals and status counts")
        },
    )
    def get(self, request: Request) -> Response:
        return Response(services.reconciliation_summary())
