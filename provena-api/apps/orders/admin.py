from django.contrib import admin

from .models import Order, OrderDispute, OrderItem, SubOrder


class SubOrderInline(admin.TabularInline):
    model = SubOrder
    extra = 0
    readonly_fields = ["id", "supplier", "status", "subtotal", "tracking_number", "created_at"]
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
    ]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "reference",
        "buyer",
        "status",
        "total_amount",
        "shipping_city",
        "shipping_country",
        "created_at",
    ]
    list_filter = ["status", "shipping_country", "created_at"]
    search_fields = ["reference", "buyer__email", "shipping_name"]
    readonly_fields = ["id", "reference", "buyer", "total_amount", "created_at", "updated_at"]
    inlines = [SubOrderInline]


@admin.register(SubOrder)
class SubOrderAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "order",
        "supplier",
        "status",
        "subtotal",
        "tracking_number",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["order__reference", "supplier__business_name", "tracking_number"]
    readonly_fields = ["id", "order", "supplier", "subtotal", "created_at", "updated_at"]
    inlines = [OrderItemInline]


@admin.register(OrderDispute)
class OrderDisputeAdmin(admin.ModelAdmin):
    list_display = ["id", "sub_order", "raised_by", "status", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["sub_order__order__reference", "raised_by__email"]
    readonly_fields = ["id", "sub_order", "raised_by", "created_at", "updated_at"]
