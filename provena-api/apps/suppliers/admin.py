from django.contrib import admin

from .models import Supplier, SupplierAddress, SupplierDocument


class SupplierAddressInline(admin.StackedInline):
    model = SupplierAddress
    extra = 0


class SupplierDocumentInline(admin.TabularInline):
    model = SupplierDocument
    extra = 0
    readonly_fields = ["uploaded_at", "reviewed_at", "reviewed_by"]


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = [
        "business_name",
        "user",
        "status",
        "commission_rate",
        "stripe_onboarding_complete",
        "created_at",
    ]
    list_filter = ["status", "stripe_onboarding_complete"]
    search_fields = ["business_name", "user__email"]
    prepopulated_fields = {"slug": ("business_name",)}
    readonly_fields = ["id", "created_at", "updated_at", "stripe_account_id"]
    inlines = [SupplierAddressInline, SupplierDocumentInline]
    actions = ["approve_suppliers", "suspend_suppliers"]

    @admin.action(description="Approve selected suppliers")
    def approve_suppliers(self, request, queryset):
        from .services import approve_supplier

        for supplier in queryset:
            approve_supplier(supplier, request.user)

    @admin.action(description="Suspend selected suppliers")
    def suspend_suppliers(self, request, queryset):
        from .services import suspend_supplier

        for supplier in queryset:
            suspend_supplier(supplier, request.user)


@admin.register(SupplierDocument)
class SupplierDocumentAdmin(admin.ModelAdmin):
    list_display = [
        "supplier",
        "document_type",
        "status",
        "uploaded_at",
        "reviewed_at",
        "reviewed_by",
    ]
    list_filter = ["document_type", "status"]
    search_fields = ["supplier__business_name"]
    readonly_fields = ["id", "uploaded_at"]
