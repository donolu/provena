from rest_framework import serializers

from .models import (
    ALLOWED_ATTACHMENT_TYPES,
    ATTACHMENT_MAX_BYTES,
    Dispute,
    DisputeAttachment,
    DisputeEvent,
    DisputeMessage,
    DisputeOutcome,
    DisputeRefund,
    DisputeType,
)


class DisputeEventSerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(source="author.email", read_only=True)

    class Meta:
        model = DisputeEvent
        fields = ["id", "event_type", "author_email", "body", "created_at"]


class DisputeMessageSerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(source="author.email", read_only=True)

    class Meta:
        model = DisputeMessage
        fields = ["id", "author_email", "body", "created_at"]


class DisputeAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(source="uploaded_by.email", read_only=True)
    url = serializers.SerializerMethodField()

    class Meta:
        model = DisputeAttachment
        fields = [
            "id",
            "filename",
            "content_type",
            "size_bytes",
            "uploaded_by_email",
            "url",
            "created_at",
        ]

    def get_url(self, obj: DisputeAttachment) -> str:
        from . import services

        try:
            return services.attachment_public_url(obj)
        except Exception:
            return ""


class DisputeRefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisputeRefund
        fields = ["id", "stripe_refund_id", "amount_pence", "status", "created_at"]


class DisputeListSerializer(serializers.ModelSerializer):
    opened_by_email = serializers.EmailField(source="opened_by.email", read_only=True)
    respondent_email = serializers.EmailField(source="respondent.email", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Dispute
        fields = [
            "id",
            "sub_order",
            "dispute_type",
            "status",
            "resolution_requested",
            "outcome",
            "opened_by_email",
            "respondent_email",
            "response_deadline",
            "is_overdue",
            "opened_at",
        ]


class DisputeDetailSerializer(serializers.ModelSerializer):
    opened_by_email = serializers.EmailField(source="opened_by.email", read_only=True)
    respondent_email = serializers.EmailField(source="respondent.email", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    events = DisputeEventSerializer(many=True, read_only=True)
    messages = DisputeMessageSerializer(many=True, read_only=True)
    attachments = DisputeAttachmentSerializer(many=True, read_only=True)
    refunds = DisputeRefundSerializer(many=True, read_only=True)

    class Meta:
        model = Dispute
        fields = [
            "id",
            "sub_order",
            "dispute_type",
            "description",
            "resolution_requested",
            "status",
            "outcome",
            "outcome_amount_pence",
            "outcome_notes",
            "opened_by_email",
            "respondent_email",
            "response_deadline",
            "payout_held",
            "is_overdue",
            "opened_at",
            "resolved_at",
            "events",
            "messages",
            "attachments",
            "refunds",
        ]


class OpenDisputeSerializer(serializers.Serializer):
    sub_order_id = serializers.UUIDField()
    dispute_type = serializers.ChoiceField(choices=DisputeType.choices)
    description = serializers.CharField(min_length=10, max_length=2000)
    resolution_requested = serializers.ChoiceField(
        choices=[
            ("FULL_REFUND", "Full refund"),
            ("PARTIAL_REFUND", "Partial refund"),
            ("REPLACEMENT", "Replacement"),
            ("NO_ACTION", "No action"),
        ]
    )


class RespondDisputeSerializer(serializers.Serializer):
    body = serializers.CharField(min_length=10, max_length=2000)


class EscalateDisputeSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=2000, required=False, default="")


class ResolveDisputeSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=DisputeOutcome.choices)
    outcome_amount_pence = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    outcome_notes = serializers.CharField(max_length=2000, required=False, default="")

    def validate(self, attrs):
        if attrs.get("outcome") == "PARTIAL_REFUND" and not attrs.get("outcome_amount_pence"):
            raise serializers.ValidationError(
                {"outcome_amount_pence": "Required for a partial refund outcome."}
            )
        return attrs


class CloseDisputeSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=2000, required=False, default="")


class TriggerRefundSerializer(serializers.Serializer):
    stripe_refund_id = serializers.CharField(max_length=100)
    amount_pence = serializers.IntegerField(min_value=1)


class PostMessageSerializer(serializers.Serializer):
    body = serializers.CharField(min_length=1, max_length=5000)


class RequestAttachmentUploadSerializer(serializers.Serializer):
    filename = serializers.CharField(max_length=255)
    content_type = serializers.ChoiceField(choices=sorted(ALLOWED_ATTACHMENT_TYPES))
    size_bytes = serializers.IntegerField(min_value=1, max_value=ATTACHMENT_MAX_BYTES)
