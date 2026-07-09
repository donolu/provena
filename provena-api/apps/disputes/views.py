from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role, User
from apps.orders.models import SubOrder
from apps.pagination import PaginatedListMixin

from . import services
from .models import Dispute, DisputeStatus, DisputeType
from .permissions import IsAdmin, IsDisputePartyOrAdmin
from .serializers import (
    CloseDisputeSerializer,
    DisputeAttachmentSerializer,
    DisputeDetailSerializer,
    DisputeListSerializer,
    DisputeMessageSerializer,
    DisputeRefundSerializer,
    EscalateDisputeSerializer,
    OpenDisputeSerializer,
    PostMessageSerializer,
    RequestAttachmentUploadSerializer,
    ResolveDisputeSerializer,
    RespondDisputeSerializer,
    TriggerRefundSerializer,
)

_SUPPLIER_ONLY_TYPES = {
    DisputeType.FALSE_CLAIM,
    DisputeType.DELIVERY_REFUSED,
    DisputeType.FRAUDULENT_CANCELLATION,
}


class DisputeListCreateView(PaginatedListMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=DisputeListSerializer(many=True))
    def get(self, request: Request) -> Response:
        qs = Dispute.objects.filter(
            Q(opened_by=request.user) | Q(respondent=request.user)
        ).select_related("opened_by", "respondent", "sub_order")
        return self.paginate(qs, DisputeListSerializer, request)

    @extend_schema(request=OpenDisputeSerializer, responses={201: DisputeDetailSerializer})
    def post(self, request: Request) -> Response:
        ser = OpenDisputeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        sub_order = get_object_or_404(SubOrder, id=data["sub_order_id"])

        user = request.user
        buyer = sub_order.order.buyer
        supplier_user = sub_order.supplier.user

        if user.id not in (buyer.id, supplier_user.id):
            return Response(
                {"detail": "You are not a party to this sub-order."},
                status=status.HTTP_403_FORBIDDEN,
            )

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
            Dispute.objects.prefetch_related(
                "events__author", "messages__author", "attachments__uploaded_by", "refunds"
            ),
            pk=pk,
        )
        self.check_object_permissions(self.request, dispute)
        return dispute

    @extend_schema(responses=DisputeDetailSerializer)
    def get(self, request: Request, pk) -> Response:
        return Response(DisputeDetailSerializer(self._get_dispute(pk)).data)


class DisputeRespondView(APIView):
    permission_classes = [IsAuthenticated, IsDisputePartyOrAdmin]

    @extend_schema(request=RespondDisputeSerializer, responses=DisputeDetailSerializer)
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

    @extend_schema(request=EscalateDisputeSerializer, responses=DisputeDetailSerializer)
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

        from apps.notifications.services import notify

        for admin in User.objects.filter(role=Role.ADMIN):
            notify(
                recipient=admin,
                title="Dispute escalated",
                body=f"A dispute on order {dispute.sub_order} has been escalated and needs attention.",
                data={"dispute_id": str(dispute.id)},
            )
        return Response(DisputeDetailSerializer(dispute).data)


class DisputeResolveView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(request=ResolveDisputeSerializer, responses=DisputeDetailSerializer)
    def post(self, request: Request, pk) -> Response:
        dispute = get_object_or_404(
            Dispute.objects.select_related("sub_order__order__payment", "sub_order__supplier"),
            pk=pk,
        )

        if dispute.status not in (DisputeStatus.ESCALATED, DisputeStatus.RESOLVING):
            return Response(
                {"detail": "Only escalated disputes can be resolved or retried."},
                status=status.HTTP_409_CONFLICT,
            )

        ser = ResolveDisputeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        try:
            dispute = services.resolve_dispute(
                dispute=dispute,
                admin=request.user,
                outcome=d["outcome"],
                outcome_amount_pence=d.get("outcome_amount_pence"),
                outcome_notes=d.get("outcome_notes", ""),
            )
        except Exception as exc:
            return Response(
                {"detail": f"Failed to process refund: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(DisputeDetailSerializer(dispute).data)


class DisputeCloseView(APIView):
    permission_classes = [IsAuthenticated, IsDisputePartyOrAdmin]

    @extend_schema(request=CloseDisputeSerializer, responses=DisputeDetailSerializer)
    def post(self, request: Request, pk) -> Response:
        dispute = get_object_or_404(Dispute, pk=pk)
        self.check_object_permissions(request, dispute)

        if dispute.status in (DisputeStatus.RESOLVED, DisputeStatus.CLOSED):
            return Response(
                {"detail": "Dispute is already resolved or closed."},
                status=status.HTTP_409_CONFLICT,
            )

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
# Message thread (#38)
# ---------------------------------------------------------------------------


class DisputeMessageView(APIView):
    permission_classes = [IsAuthenticated, IsDisputePartyOrAdmin]

    def _get_dispute(self, pk, request):
        dispute = get_object_or_404(Dispute, pk=pk)
        self.check_object_permissions(request, dispute)
        return dispute

    @extend_schema(responses=DisputeMessageSerializer(many=True))
    def get(self, request: Request, pk) -> Response:
        dispute = self._get_dispute(pk, request)
        return Response(
            DisputeMessageSerializer(
                dispute.messages.select_related("author").all(), many=True
            ).data
        )

    @extend_schema(request=PostMessageSerializer, responses={201: DisputeMessageSerializer})
    def post(self, request: Request, pk) -> Response:
        dispute = self._get_dispute(pk, request)

        is_admin = request.user.role == Role.ADMIN  # type: ignore[union-attr]
        if not is_admin and dispute.status in (DisputeStatus.RESOLVED, DisputeStatus.CLOSED):
            return Response(
                {"detail": "Messaging is closed on resolved or closed disputes."},
                status=status.HTTP_409_CONFLICT,
            )

        ser = PostMessageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        message = services.post_message(dispute, request.user, ser.validated_data["body"])
        return Response(DisputeMessageSerializer(message).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# File evidence uploads (#37)
# ---------------------------------------------------------------------------


class DisputeAttachmentView(APIView):
    permission_classes = [IsAuthenticated, IsDisputePartyOrAdmin]

    def _get_dispute(self, pk, request):
        dispute = get_object_or_404(Dispute, pk=pk)
        self.check_object_permissions(request, dispute)
        return dispute

    @extend_schema(
        request=RequestAttachmentUploadSerializer,
        responses={
            201: {
                "type": "object",
                "properties": {
                    "attachment": {"$ref": "#/components/schemas/DisputeAttachment"},
                    "upload_url": {"type": "string"},
                },
            }
        },
    )
    def post(self, request: Request, pk) -> Response:
        dispute = self._get_dispute(pk, request)

        if dispute.status in (DisputeStatus.RESOLVED, DisputeStatus.CLOSED):
            return Response(
                {"detail": "Cannot add attachments to resolved or closed disputes."},
                status=status.HTTP_409_CONFLICT,
            )

        ser = RequestAttachmentUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        try:
            attachment, upload_url = services.generate_attachment_upload_url(
                dispute=dispute,
                uploaded_by=request.user,
                filename=d["filename"],
                content_type=d["content_type"],
                size_bytes=d["size_bytes"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"detail": f"Could not generate upload URL: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "attachment": DisputeAttachmentSerializer(attachment).data,
                "upload_url": upload_url,
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Admin views
# ---------------------------------------------------------------------------


class AdminDisputeListView(PaginatedListMixin, APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(responses=DisputeListSerializer(many=True))
    def get(self, request: Request) -> Response:
        qs = Dispute.objects.select_related("opened_by", "respondent", "sub_order")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        overdue = request.query_params.get("overdue")
        if overdue == "1":
            from django.utils import timezone

            qs = qs.filter(status=DisputeStatus.OPEN, response_deadline__lt=timezone.now())
        return self.paginate(qs, DisputeListSerializer, request)


class AdminDisputeRefundView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(request=TriggerRefundSerializer, responses={201: DisputeRefundSerializer})
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
        return Response(DisputeRefundSerializer(refund).data, status=status.HTTP_201_CREATED)
