from decimal import Decimal

from rest_framework import serializers

from .models import Payment, Payout


class PaymentSerializer(serializers.ModelSerializer):
    order_reference = serializers.CharField(source="order.reference", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "order_reference",
            "amount",
            "currency",
            "status",
            "status_display",
            "refunded_amount",
            "stripe_payment_intent_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class RefundSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=Decimal("0.01"),
        help_text="Amount to refund in GBP. Omit for a full refund.",
    )


class CreatePaymentIntentSerializer(serializers.Serializer):
    order_reference = serializers.CharField()


class PaymentIntentResponseSerializer(serializers.Serializer):
    client_secret = serializers.CharField()
    payment_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class PayoutSerializer(serializers.ModelSerializer):
    sub_order_id = serializers.UUIDField(source="sub_order.id", read_only=True)
    order_reference = serializers.CharField(source="sub_order.order.reference", read_only=True)
    supplier_name = serializers.CharField(source="supplier.business_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Payout
        fields = [
            "id",
            "sub_order_id",
            "order_reference",
            "supplier_name",
            "gross_amount",
            "platform_fee",
            "net_amount",
            "status",
            "status_display",
            "stripe_transfer_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
