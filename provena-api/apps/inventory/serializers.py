from rest_framework import serializers

from .models import StockLevel, StockLot, StockMovement


class StockLevelSerializer(serializers.ModelSerializer):
    variant_sku = serializers.CharField(source="variant.sku", read_only=True)
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    quantity_on_hand = serializers.IntegerField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = StockLevel
        fields = [
            "id",
            "variant_sku",
            "product_name",
            "quantity_available",
            "quantity_reserved",
            "quantity_on_hand",
            "low_stock_threshold",
            "is_low_stock",
            "updated_at",
        ]
        read_only_fields = ["id", "quantity_available", "quantity_reserved", "updated_at"]


class StockLotSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockLot
        fields = [
            "id",
            "lot_number",
            "quantity_received",
            "quantity_remaining",
            "received_at",
            "expires_at",
            "notes",
        ]
        read_only_fields = ["id", "quantity_remaining", "received_at"]


class StockMovementSerializer(serializers.ModelSerializer):
    movement_type_display = serializers.CharField(
        source="get_movement_type_display", read_only=True
    )
    performed_by_email = serializers.SerializerMethodField()

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "movement_type",
            "movement_type_display",
            "quantity",
            "quantity_after",
            "reference",
            "notes",
            "performed_by_email",
            "created_at",
        ]
        read_only_fields = fields

    def get_performed_by_email(self, obj) -> str | None:
        return obj.performed_by.email if obj.performed_by else None


class ReceiveStockSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
    lot_number = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    expires_at = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class AdjustStockSerializer(serializers.Serializer):
    delta = serializers.IntegerField()
    notes = serializers.CharField()

    def validate_delta(self, value: int) -> int:
        if value == 0:
            raise serializers.ValidationError("Delta cannot be zero.")
        return value


class SetThresholdSerializer(serializers.Serializer):
    low_stock_threshold = serializers.IntegerField(min_value=0)
