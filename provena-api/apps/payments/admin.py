from django.contrib import admin

from .models import Payment, Payout


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "amount", "currency", "status", "created_at"]
    list_filter = ["status", "currency", "created_at"]
    search_fields = ["order__reference", "stripe_payment_intent_id"]
    readonly_fields = [
        "id",
        "order",
        "stripe_payment_intent_id",
        "amount",
        "currency",
        "created_at",
        "updated_at",
    ]


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "supplier",
        "sub_order",
        "gross_amount",
        "platform_fee",
        "net_amount",
        "status",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = [
        "supplier__business_name",
        "sub_order__order__reference",
        "stripe_transfer_id",
    ]
    readonly_fields = [
        "id",
        "sub_order",
        "supplier",
        "gross_amount",
        "platform_fee",
        "net_amount",
        "created_at",
        "updated_at",
    ]
