from django.contrib import admin

from .models import DiscountCode, DiscountRedemption, Order, OrderItem, SubOrder


class SubOrderInline(admin.TabularInline):
    model = SubOrder
    extra = 0
    readonly_fields = [
        "id",
        "supplier",
        "status",
        "goods_subtotal",
        "vat_amount",
        "subtotal",
        "tracking_number",
        "created_at",
    ]
    show_change_link = True


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = [
        "id",
        "variant",
        "product_name",
        "variant_name",
        "sku",
        "quantity",
        "unit_price",
        "vat_rate",
        "vat_amount",
    ]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "reference",
        "buyer",
        "status",
        "goods_subtotal",
        "vat_amount",
        "total_amount",
        "shipping_city",
        "shipping_country",
        "created_at",
    ]
    list_filter = ["status", "shipping_country", "created_at"]
    search_fields = ["reference", "buyer__email", "shipping_name"]
    readonly_fields = [
        "id",
        "reference",
        "buyer",
        "goods_subtotal",
        "discount_amount",
        "shipping_amount",
        "vat_amount",
        "total_amount",
        "created_at",
        "updated_at",
    ]
    inlines = [SubOrderInline]


@admin.register(SubOrder)
class SubOrderAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "order",
        "supplier",
        "status",
        "goods_subtotal",
        "vat_amount",
        "subtotal",
        "tracking_number",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["order__reference", "supplier__business_name", "tracking_number"]
    readonly_fields = [
        "id",
        "order",
        "supplier",
        "goods_subtotal",
        "discount_amount",
        "shipping_amount",
        "vat_amount",
        "subtotal",
        "created_at",
        "updated_at",
    ]
    inlines = [OrderItemInline]


@admin.register(DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "discount_type",
        "value",
        "funded_by",
        "is_active",
        "valid_from",
        "valid_until",
        "times_used",
    ]
    list_filter = ["discount_type", "funded_by", "is_active"]
    search_fields = ["code"]
    readonly_fields = ["id", "created_at", "updated_at"]

    @admin.display(description="Times used")
    def times_used(self, obj: DiscountCode) -> int:
        return obj.redemptions.count()


@admin.register(DiscountRedemption)
class DiscountRedemptionAdmin(admin.ModelAdmin):
    list_display = ["code", "buyer", "order", "amount", "created_at"]
    search_fields = ["code__code", "buyer__email", "order__reference"]
    readonly_fields = ["id", "code", "buyer", "order", "amount", "created_at"]

    def has_add_permission(self, request) -> bool:
        return False
