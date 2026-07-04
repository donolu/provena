from django.contrib import admin

from .models import Cart, CartItem, Review, WishlistItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ["id", "variant", "quantity", "added_at"]


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["id", "buyer", "item_count", "created_at"]
    search_fields = ["buyer__email"]
    readonly_fields = ["id", "buyer", "created_at", "updated_at"]
    inlines = [CartItemInline]

    @admin.display(description="Items")
    def item_count(self, obj):
        return obj.items.count()


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ["id", "buyer", "variant", "added_at"]
    search_fields = ["buyer__email", "variant__sku"]
    readonly_fields = ["id", "buyer", "variant", "added_at"]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "variant",
        "reviewer",
        "rating",
        "is_verified_purchase",
        "is_approved",
        "created_at",
    ]
    list_filter = ["is_approved", "is_verified_purchase", "rating"]
    search_fields = ["variant__sku", "reviewer__email", "title"]
    readonly_fields = [
        "id",
        "variant",
        "reviewer",
        "is_verified_purchase",
        "created_at",
        "updated_at",
    ]
    actions = ["approve_selected"]

    @admin.action(description="Approve selected reviews")
    def approve_selected(self, request, queryset):
        queryset.update(is_approved=True)
