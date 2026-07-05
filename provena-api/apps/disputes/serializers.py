from rest_framework import serializers

from .models import (
    Dispute,
    DisputeEvent,
    DisputeOutcome,
    DisputeRefund,
    DisputeType,
)


class DisputeEventSerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(source="author.email", read_only=True)

    class Meta:
        model = DisputeEvent
        fields = ["id", "event_type", "author_email", "body", "created_at"]


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
