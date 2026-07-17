from decimal import Decimal

from rest_framework import serializers

from .models import DiscountCode, DiscountType, Order, OrderItem, OrderReturn, SubOrder


class OrderItemSerializer(serializers.ModelSerializer):
    total_price = serializers.DecimalField(read_only=True, max_digits=12, decimal_places=2)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product_name",
            "variant_name",
            "sku",
            "quantity",
            "unit_price",
            "total_price",
            "vat_rate",
            "vat_amount",
        ]


class OrderReturnSerializer(serializers.ModelSerializer):
    raised_by_email = serializers.SerializerMethodField()
    sub_order_id = serializers.UUIDField(source="sub_order.id", read_only=True)
    order_reference = serializers.CharField(source="sub_order.order.reference", read_only=True)
    supplier_name = serializers.CharField(source="sub_order.supplier.business_name", read_only=True)

    class Meta:
        model = OrderReturn
        fields = [
            "id",
            "sub_order_id",
            "order_reference",
            "supplier_name",
            "reason",
            "status",
            "supplier_notes",
            "refund_amount",
            "raised_by_email",
            "created_at",
            "updated_at",
        ]

    def get_raised_by_email(self, obj) -> str | None:
        return obj.raised_by.email if obj.raised_by else None


class SubOrderSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.business_name", read_only=True)
    supplier_slug = serializers.SlugField(source="supplier.slug", read_only=True)
    supplier_vat_number = serializers.CharField(source="supplier.vat_number", read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    returns = OrderReturnSerializer(many=True, read_only=True)

    class Meta:
        model = SubOrder
        fields = [
            "id",
            "supplier_name",
            "supplier_slug",
            "supplier_vat_number",
            "status",
            "goods_subtotal",
            "discount_amount",
            "shipping_amount",
            "vat_amount",
            "subtotal",
            "fulfilment_mode",
            "tracking_number",
            "delivered_at",
            "items",
            "returns",
            "created_at",
            "updated_at",
        ]


class SubOrderListSerializer(serializers.ModelSerializer):
    """Lighter serialiser for supplier list views — no nested items."""

    supplier_name = serializers.CharField(source="supplier.business_name", read_only=True)
    order_reference = serializers.CharField(source="order.reference", read_only=True)
    buyer_email = serializers.EmailField(source="order.buyer.email", read_only=True)

    class Meta:
        model = SubOrder
        fields = [
            "id",
            "order_reference",
            "buyer_email",
            "supplier_name",
            "status",
            "goods_subtotal",
            "discount_amount",
            "shipping_amount",
            "vat_amount",
            "subtotal",
            "tracking_number",
            "created_at",
        ]


class OrderSerializer(serializers.ModelSerializer):
    buyer_email = serializers.EmailField(source="buyer.email", read_only=True)
    sub_orders = SubOrderSerializer(many=True, read_only=True)
    payment_id = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    refunded_amount = serializers.SerializerMethodField()

    def get_payment_id(self, obj) -> str | None:
        payment = getattr(obj, "payment", None)
        return str(payment.id) if payment else None

    def get_payment_status(self, obj) -> str | None:
        payment = getattr(obj, "payment", None)
        return payment.status if payment else None

    def get_refunded_amount(self, obj) -> str | None:
        payment = getattr(obj, "payment", None)
        return str(payment.refunded_amount) if payment else None

    class Meta:
        model = Order
        fields = [
            "id",
            "reference",
            "status",
            "buyer_email",
            "shipping_name",
            "shipping_line1",
            "shipping_line2",
            "shipping_city",
            "shipping_postcode",
            "shipping_country",
            "goods_subtotal",
            "discount_amount",
            "discount_code",
            "shipping_amount",
            "vat_amount",
            "total_amount",
            "notes",
            "payment_id",
            "payment_status",
            "refunded_amount",
            "sub_orders",
            "created_at",
            "updated_at",
        ]


# --- Write serialisers ---


class OrderItemInputSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class PlaceOrderSerializer(serializers.Serializer):
    items = OrderItemInputSerializer(many=True)
    shipping_name = serializers.CharField(max_length=200)
    shipping_line1 = serializers.CharField(max_length=200)
    shipping_line2 = serializers.CharField(
        max_length=200, required=False, allow_blank=True, default=""
    )
    shipping_city = serializers.CharField(max_length=100)
    shipping_postcode = serializers.CharField(max_length=20)
    shipping_country = serializers.CharField(max_length=2)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    discount_code = serializers.CharField(
        max_length=40, required=False, allow_blank=True, default=""
    )

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("At least one item is required.")
        return items


class DispatchSerializer(serializers.Serializer):
    tracking_number = serializers.CharField(
        max_length=200, required=False, allow_blank=True, default=""
    )


class ReturnCreateSerializer(serializers.Serializer):
    reason = serializers.CharField()


class ReturnActionSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ReturnRefundSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal("0.01")
    )


# --- Discount codes ---


class DiscountValidateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=40)


class DiscountValidateResultSerializer(serializers.Serializer):
    valid = serializers.BooleanField()
    code = serializers.CharField(required=False)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    reason = serializers.CharField(required=False)


class AdminDiscountCodeSerializer(serializers.ModelSerializer):
    times_used = serializers.SerializerMethodField()

    class Meta:
        model = DiscountCode
        fields = [
            "id",
            "code",
            "discount_type",
            "value",
            "funded_by",
            "minimum_spend",
            "valid_from",
            "valid_until",
            "max_uses",
            "max_uses_per_buyer",
            "is_active",
            "times_used",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "times_used", "created_at", "updated_at"]

    def get_times_used(self, obj: DiscountCode) -> int:
        return obj.redemptions.count()

    def validate_code(self, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise serializers.ValidationError("Code cannot be blank.")
        return value

    def validate(self, attrs):
        discount_type = attrs.get("discount_type") or getattr(self.instance, "discount_type", None)
        value = attrs.get("value", getattr(self.instance, "value", None))
        if value is not None and value <= 0:
            raise serializers.ValidationError({"value": "Value must be greater than zero."})
        if (
            discount_type == DiscountType.PERCENTAGE
            and value is not None
            and value > Decimal("100")
        ):
            raise serializers.ValidationError({"value": "Percentage cannot exceed 100."})
        return attrs
