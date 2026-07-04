from django.contrib import admin

from .models import StockLevel, StockLot, StockMovement


@admin.register(StockLevel)
class StockLevelAdmin(admin.ModelAdmin):
    list_display = [
        "variant_sku",
        "product_name",
        "quantity_available",
        "quantity_reserved",
        "low_stock_threshold",
        "is_low_stock_display",
        "updated_at",
    ]
    list_filter = ["updated_at"]
    search_fields = ["variant__sku", "variant__product__name"]
    readonly_fields = ["id", "updated_at"]

    @admin.display(description="SKU")
    def variant_sku(self, obj):
        return obj.variant.sku

    @admin.display(description="Product")
    def product_name(self, obj):
        return obj.variant.product.name

    @admin.display(boolean=True, description="Low Stock?")
    def is_low_stock_display(self, obj):
        return obj.is_low_stock


@admin.register(StockLot)
class StockLotAdmin(admin.ModelAdmin):
    list_display = [
        "lot_number",
        "variant_sku",
        "quantity_received",
        "quantity_remaining",
        "received_at",
        "expires_at",
    ]
    list_filter = ["received_at", "expires_at"]
    search_fields = ["lot_number", "variant__sku"]
    readonly_fields = ["id", "received_at"]

    @admin.display(description="SKU")
    def variant_sku(self, obj):
        return obj.variant.sku


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = [
        "variant_sku",
        "movement_type",
        "quantity",
        "quantity_after",
        "reference",
        "performed_by",
        "created_at",
    ]
    list_filter = ["movement_type", "created_at"]
    search_fields = ["variant__sku", "reference"]
    readonly_fields = [
        "id",
        "variant",
        "movement_type",
        "quantity",
        "quantity_after",
        "reference",
        "notes",
        "performed_by",
        "created_at",
    ]

    @admin.display(description="SKU")
    def variant_sku(self, obj):
        return obj.variant.sku
