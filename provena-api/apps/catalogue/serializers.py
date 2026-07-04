from decimal import Decimal

from rest_framework import serializers

from .models import Banner, Category, Product, ProductImage, ProductVariant


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    parent_slug = serializers.SlugField(source="parent.slug", read_only=True, allow_null=True)
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "image_url",
            "parent_slug",
            "children",
            "position",
            "is_active",
            "product_count",
        ]

    def get_children(self, obj) -> list:
        active = obj.children.filter(is_active=True)
        return CategorySerializer(active, many=True).data

    def get_product_count(self, obj) -> int:
        return obj.products.filter(status="ACTIVE").count()


class CategoryWriteSerializer(serializers.ModelSerializer):
    parent = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Category.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Category
        fields = ["name", "description", "image_url", "parent", "position", "is_active"]

    def validate_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Category name cannot be blank.")
        return value.strip()


class ProductVariantSerializer(serializers.ModelSerializer):
    on_sale = serializers.BooleanField(read_only=True)
    discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True, allow_null=True
    )

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "name",
            "sku",
            "price",
            "compare_at_price",
            "weight_grams",
            "is_active",
            "on_sale",
            "discount_percent",
        ]
        read_only_fields = ["id", "on_sale", "discount_percent"]


class ProductVariantWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    sku = serializers.CharField(max_length=100)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    weight_grams = serializers.IntegerField(min_value=0, default=0)

    def validate_price(self, value: Decimal) -> Decimal:
        if value <= Decimal("0"):
            raise serializers.ValidationError("Price must be greater than zero.")
        return value

    def validate(self, data: dict) -> dict:
        compare = data.get("compare_at_price")
        price = data.get("price")
        if compare is not None and price is not None and compare <= price:
            raise serializers.ValidationError(
                {"compare_at_price": "Compare-at price must be greater than the selling price."}
            )
        return data


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "url", "alt_text", "position", "is_primary"]
        read_only_fields = ["id"]


class ProductImageWriteSerializer(serializers.Serializer):
    url = serializers.URLField()
    alt_text = serializers.CharField(max_length=200, allow_blank=True, default="")
    position = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    is_primary = serializers.BooleanField(default=False)


class ProductSerializer(serializers.ModelSerializer):
    supplier_slug = serializers.SlugField(source="supplier.slug", read_only=True)
    supplier_name = serializers.CharField(source="supplier.business_name", read_only=True)
    category_slug = serializers.SlugField(source="category.slug", read_only=True, allow_null=True)
    category_name = serializers.CharField(source="category.name", read_only=True, allow_null=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    def get_average_rating(self, obj) -> float | None:
        from django.db.models import Avg

        from apps.marketplace.models import Review

        result = Review.objects.filter(variant__product=obj, is_approved=True).aggregate(
            avg=Avg("rating")
        )
        avg = result["avg"]
        return round(avg, 1) if avg is not None else None

    def get_review_count(self, obj) -> int:
        from apps.marketplace.models import Review

        return Review.objects.filter(variant__product=obj, is_approved=True).count()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "status",
            "is_featured",
            "supplier_slug",
            "supplier_name",
            "category_slug",
            "category_name",
            "average_rating",
            "review_count",
            "variants",
            "images",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "status",
            "is_featured",
            "supplier_slug",
            "supplier_name",
            "category_slug",
            "category_name",
            "average_rating",
            "review_count",
            "variants",
            "images",
            "created_at",
            "updated_at",
        ]


class ProductWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(allow_blank=True, default="")
    category = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Category.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )

    def validate_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Product name cannot be blank.")
        return value.strip()


class AdminProductSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.business_name", read_only=True)
    supplier_slug = serializers.SlugField(source="supplier.slug", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True, allow_null=True)
    category_slug = serializers.SlugField(source="category.slug", read_only=True, allow_null=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "status",
            "is_featured",
            "supplier_name",
            "supplier_slug",
            "category_name",
            "category_slug",
            "variants",
            "images",
            "created_at",
            "updated_at",
        ]


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = [
            "id",
            "title",
            "subtitle",
            "image_url",
            "link",
            "is_active",
            "position",
            "created_at",
            "updated_at",
        ]


class BannerWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ["title", "subtitle", "image_url", "link", "is_active", "position"]
