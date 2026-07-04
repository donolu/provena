from django.contrib import admin

from .models import Category, Product, ProductImage, ProductVariant


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    readonly_fields = ["id", "created_at"]


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    readonly_fields = ["id"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "position", "is_active"]
    list_filter = ["is_active", "parent"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["id"]
    ordering = ["position", "name"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "supplier", "category", "status", "is_featured", "created_at"]
    list_filter = ["status", "is_featured", "category"]
    search_fields = ["name", "supplier__business_name"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [ProductVariantInline, ProductImageInline]
    actions = ["publish_products", "archive_products"]

    @admin.action(description="Publish selected products")
    def publish_products(self, request, queryset):
        from .services import publish_product

        for product in queryset:
            try:
                publish_product(product)
            except ValueError:
                pass

    @admin.action(description="Archive selected products")
    def archive_products(self, request, queryset):
        from .services import archive_product

        for product in queryset:
            archive_product(product)
