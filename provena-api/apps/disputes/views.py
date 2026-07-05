from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role, User
from apps.orders.models import SubOrder

from . import services
from .models import Dispute, DisputeStatus, DisputeType
from .permissions import IsAdmin, IsDisputePartyOrAdmin
from .serializers import (
    CloseDisputeSerializer,
    DisputeDetailSerializer,
    DisputeListSerializer,
    EscalateDisputeSerializer,
    OpenDisputeSerializer,
    ResolveDisputeSerializer,
    RespondDisputeSerializer,
    TriggerRefundSerializer,
)

# Dispute types that may only be opened by a supplier.
_SUPPLIER_ONLY_TYPES = {
    DisputeType.FALSE_CLAIM,
    DisputeType.DELIVERY_REFUSED,
    DisputeType.FRAUDULENT_CANCELLATION,
}


class DisputeListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = Dispute.objects.filter(
            Q(opened_by=request.user) | Q(respondent=request.user)
        ).select_related("opened_by", "respondent", "sub_order")
        return Response(DisputeListSerializer(qs, many=True).data)

    def post(self, request: Request) -> Response:
        ser = OpenDisputeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        sub_order = get_object_or_404(SubOrder, id=data["sub_order_id"])

        # Validate the opener is a party to this sub-order.
        user = request.user
        buyer = sub_order.order.buyer
        supplier_user = sub_order.supplier.user

        if user.id not in (buyer.id, supplier_user.id):
            return Response(
                {"detail": "You are not a party to this sub-order."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Supplier-only dispute types
        if data["dispute_type"] in _SUPPLIER_ONLY_TYPES and user.id != supplier_user.id:
            return Response(
                {"detail": "This dispute type may only be raised by the supplier."},
                status=status.HTTP_403_FORBIDDEN,
            )

        respondent = supplier_user if user.id == buyer.id else buyer

        dispute = services.open_dispute(
            sub_order=sub_order,
            opened_by=user,
            respondent=respondent,
            dispute_type=data["dispute_type"],
            description=data["description"],
            resolution_requested=data["resolution_requested"],
        )
        return Response(DisputeDetailSerializer(dispute).data, status=status.HTTP_201_CREATED)


class DisputeDetailView(APIView):
    permission_classes = [IsAuthenticated, IsDisputePartyOrAdmin]

    def _get_dispute(self, pk):
        dispute = get_object_or_404(
            Dispute.objects.prefetch_related("events__author", "refunds"),
            pk=pk,
        )
        self.check_object_permissions(self.request, dispute)
        return dispute

    def get(self, request: Request, pk) -> Response:
        return Response(DisputeDetailSerializer(self._get_dispute(pk)).data)


class DisputeRespondView(APIView):
    permission_classes = [IsAuthenticated, IsDisputePartyOrAdmin]

    def post(self, request: Request, pk) -> Response:
        dispute = get_object_or_404(Dispute, pk=pk)
        self.check_object_permissions(request, dispute)

        if request.user.id != dispute.respondent_id:
            return Response(
                {"detail": "Only the respondent may reply."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if dispute.status not in (DisputeStatus.OPEN, DisputeStatus.ESCALATED):
            return Response(
                {"detail": "Dispute is not in a state that accepts responses."},
                status=status.HTTP_409_CONFLICT,
            )

        ser = RespondDisputeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        dispute = services.respond_to_dispute(dispute, request.user, ser.validated_data["body"])
        return Response(DisputeDetailSerializer(dispute).data)


class DisputeEscalateView(APIView):
    permission_classes = [IsAuthenticated, IsDisputePartyOrAdmin]

    def post(self, request: Request, pk) -> Response:
        dispute = get_object_or_404(Dispute, pk=pk)
        self.check_object_permissions(request, dispute)

        if dispute.status in (DisputeStatus.RESOLVED, DisputeStatus.CLOSED):
            return Response(
                {"detail": "Cannot escalate a resolved or closed dispute."},
                status=status.HTTP_409_CONFLICT,
            )

        ser = EscalateDisputeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        dispute = services.escalate_dispute(
            dispute, request.user, ser.validated_data.get("body", "")
        )

        # Notify all admins.
        admin_qs = User.objects.filter(role=Role.ADMIN)
        from apps.notifications.services import notify

        for admin in admin_qs:
            notify(
                recipient=admin,
                title="Dispute escalated",
                body=f"A dispute on order {dispute.sub_order} has been escalated and needs attention.",
                data={"dispute_id": str(dispute.id)},
            )
        return Response(DisputeDetailSerializer(dispute).data)


class DisputeResolveView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request: Request, pk) -> Response:
        dispute = get_object_or_404(Dispute, pk=pk)

        if dispute.status != DisputeStatus.ESCALATED:
            return Response(
                {"detail": "Only escalated disputes can be resolved."},
                status=status.HTTP_409_CONFLICT,
            )

        ser = ResolveDisputeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        dispute = services.resolve_dispute(
            dispute=dispute,
            admin=request.user,
            outcome=d["outcome"],
            outcome_amount_pence=d.get("outcome_amount_pence"),
            outcome_notes=d.get("outcome_notes", ""),
        )
        return Response(DisputeDetailSerializer(dispute).data)


class DisputeCloseView(APIView):
    permission_classes = [IsAuthenticated, IsDisputePartyOrAdmin]

    def post(self, request: Request, pk) -> Response:
        dispute = get_object_or_404(Dispute, pk=pk)
        self.check_object_permissions(request, dispute)

        if dispute.status in (DisputeStatus.RESOLVED, DisputeStatus.CLOSED):
            return Response(
                {"detail": "Dispute is already resolved or closed."},
                status=status.HTTP_409_CONFLICT,
            )

        # Only opener or admin may close.
        if request.user.role != Role.ADMIN and request.user.id != dispute.opened_by_id:  # type: ignore[union-attr]
            return Response(
                {"detail": "Only the opener or an admin can close a dispute."},
                status=status.HTTP_403_FORBIDDEN,
            )

        ser = CloseDisputeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        dispute = services.close_dispute(dispute, request.user, ser.validated_data.get("body", ""))
        return Response(DisputeDetailSerializer(dispute).data)


# ---------------------------------------------------------------------------
# Admin views
# ---------------------------------------------------------------------------


class AdminDisputeListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request: Request) -> Response:
        qs = Dispute.objects.select_related("opened_by", "respondent", "sub_order")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        overdue = request.query_params.get("overdue")
        if overdue == "1":
            from django.utils import timezone

            qs = qs.filter(status=DisputeStatus.OPEN, response_deadline__lt=timezone.now())
        return Response(DisputeListSerializer(qs, many=True).data)


class AdminDisputeRefundView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request: Request, pk) -> Response:

        dispute = get_object_or_404(Dispute, pk=pk)

        if dispute.status != DisputeStatus.RESOLVED:
            return Response(
                {"detail": "Refund can only be triggered on resolved disputes."},
                status=status.HTTP_409_CONFLICT,
            )
        if dispute.outcome not in ("FULL_REFUND", "PARTIAL_REFUND"):
            return Response(
                {"detail": "Dispute outcome does not require a refund."},
                status=status.HTTP_409_CONFLICT,
            )

        ser = TriggerRefundSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        refund = services.trigger_refund(
            dispute=dispute,
            admin=request.user,
            stripe_refund_id=d["stripe_refund_id"],
            amount_pence=d["amount_pence"],
        )
        from .serializers import DisputeRefundSerializer

        return Response(DisputeRefundSerializer(refund).data, status=status.HTTP_201_CREATED)
