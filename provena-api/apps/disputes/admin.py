from django.contrib import admin

from .models import Dispute, DisputeEvent, DisputeRefund


class DisputeEventInline(admin.TabularInline):
    model = DisputeEvent
    extra = 0
    readonly_fields = ["author", "event_type", "body", "created_at"]
    can_delete = False


class DisputeRefundInline(admin.TabularInline):
    model = DisputeRefund
    extra = 0
    readonly_fields = ["stripe_refund_id", "amount_pence", "status", "created_at"]
    can_delete = False


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "sub_order",
        "dispute_type",
        "status",
        "outcome",
        "opened_by",
        "respondent",
        "opened_at",
        "is_overdue",
    ]
    list_filter = ["status", "dispute_type", "outcome"]
    search_fields = ["opened_by__email", "respondent__email"]
    readonly_fields = ["opened_at", "resolved_at", "payout_held", "is_overdue"]
    inlines = [DisputeEventInline, DisputeRefundInline]

    @admin.display(boolean=True)
    def is_overdue(self, obj):
        return obj.is_overdue


@admin.register(DisputeRefund)
class DisputeRefundAdmin(admin.ModelAdmin):
    list_display = ["id", "dispute", "stripe_refund_id", "amount_pence", "status", "created_at"]
    list_filter = ["status"]
    readonly_fields = ["created_at", "updated_at"]
