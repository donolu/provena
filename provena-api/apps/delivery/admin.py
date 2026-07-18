from django.contrib import admin

from .models import CourierDelivery


@admin.register(CourierDelivery)
class CourierDeliveryAdmin(admin.ModelAdmin):
    list_display = [
        "sub_order",
        "provider",
        "status",
        "fee_charged",
        "courier_cost",
        "provider_delivery_id",
        "created_at",
    ]
    list_filter = ["provider", "status"]
    search_fields = ["sub_order__order__reference", "provider_delivery_id", "provider_quote_id"]
    readonly_fields = [f.name for f in CourierDelivery._meta.fields]

    def has_add_permission(self, request) -> bool:
        return False
