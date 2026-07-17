from decimal import Decimal

from rest_framework import serializers

from .models import DocumentType, Supplier, SupplierAddress, SupplierDocument


class SupplierAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierAddress
        fields = ["line1", "line2", "city", "county", "postcode", "country"]


class SupplierDocumentSerializer(serializers.ModelSerializer):
    reviewed_by_email = serializers.EmailField(source="reviewed_by.email", read_only=True)

    class Meta:
        model = SupplierDocument
        fields = [
            "id",
            "document_type",
            "file_url",
            "status",
            "notes",
            "uploaded_at",
            "reviewed_at",
            "reviewed_by_email",
        ]
        read_only_fields = [
            "id",
            "status",
            "notes",
            "uploaded_at",
            "reviewed_at",
            "reviewed_by_email",
        ]


class UploadDocumentSerializer(serializers.Serializer):
    document_type = serializers.ChoiceField(choices=DocumentType.choices)
    file_url = serializers.URLField()


class DocumentReviewSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    notes = serializers.CharField(allow_blank=True, default="")


class SupplierPublicSerializer(serializers.ModelSerializer):
    address = SupplierAddressSerializer(read_only=True)
    average_rating = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = [
            "id",
            "business_name",
            "slug",
            "description",
            "logo_url",
            "website",
            "address",
            "fulfilment_mode",
            "platform_delivery_fee",
            "shipping_policy",
            "shipping_flat_rate",
            "shipping_per_item_rate",
            "free_shipping_threshold",
            "average_rating",
            "product_count",
        ]

    def get_average_rating(self, obj: "Supplier") -> float | None:
        # Prefer the queryset annotation injected by SupplierListView to avoid N+1.
        if hasattr(obj, "avg_rating"):
            avg = obj.avg_rating
            return round(float(avg), 1) if avg is not None else None
        from django.db.models import Avg

        from apps.marketplace.models import Review

        result = Review.objects.filter(variant__product__supplier=obj, is_approved=True).aggregate(
            avg=Avg("rating")
        )
        avg = result["avg"]
        return round(avg, 1) if avg is not None else None

    def get_product_count(self, obj: "Supplier") -> int:
        if hasattr(obj, "active_product_count"):
            return int(obj.active_product_count)
        return int(obj.products.filter(status="ACTIVE").count())


class SupplierProfileSerializer(serializers.ModelSerializer):
    address = SupplierAddressSerializer(required=False)
    documents = SupplierDocumentSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Supplier
        fields = [
            "id",
            "user_email",
            "business_name",
            "slug",
            "description",
            "logo_url",
            "website",
            "phone",
            "status",
            "commission_rate",
            "vat_registered",
            "vat_number",
            "fulfilment_mode",
            "platform_delivery_fee",
            "shipping_policy",
            "shipping_flat_rate",
            "shipping_per_item_rate",
            "free_shipping_threshold",
            "stripe_onboarding_complete",
            "address",
            "documents",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "user_email",
            "slug",
            "status",
            "commission_rate",
            "vat_registered",
            # Platform-brokered delivery is a platform arrangement, not self-serve (ADR-013).
            "fulfilment_mode",
            "platform_delivery_fee",
            "stripe_onboarding_complete",
            "documents",
            "created_at",
        ]

    def validate_business_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Business name cannot be blank.")
        return value.strip()

    def validate_shipping_flat_rate(self, value):
        if value < Decimal("0"):
            raise serializers.ValidationError("Shipping flat rate cannot be negative.")
        return value

    def validate_shipping_per_item_rate(self, value):
        if value < Decimal("0"):
            raise serializers.ValidationError("Shipping per-item rate cannot be negative.")
        return value

    def validate_free_shipping_threshold(self, value):
        if value is not None and value < Decimal("0"):
            raise serializers.ValidationError("Free shipping threshold cannot be negative.")
        return value


class SupplierRegistrationSerializer(serializers.Serializer):
    business_name = serializers.CharField(max_length=200)
    description = serializers.CharField(allow_blank=True, default="")
    phone = serializers.CharField(max_length=20, allow_blank=True, default="")
    website = serializers.URLField(allow_blank=True, default="", required=False)
    logo_url = serializers.URLField(allow_blank=True, default="", required=False)
    address = SupplierAddressSerializer(required=False)

    def validate_business_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Business name cannot be blank.")
        return value.strip()


class AdminSupplierSerializer(serializers.ModelSerializer):
    address = SupplierAddressSerializer(read_only=True)
    documents = SupplierDocumentSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Supplier
        fields = [
            "id",
            "user_email",
            "business_name",
            "slug",
            "description",
            "logo_url",
            "website",
            "phone",
            "status",
            "commission_rate",
            "fulfilment_mode",
            "platform_delivery_fee",
            "shipping_policy",
            "shipping_flat_rate",
            "shipping_per_item_rate",
            "free_shipping_threshold",
            "stripe_account_id",
            "stripe_onboarding_complete",
            "address",
            "documents",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_email",
            "slug",
            "stripe_account_id",
            "stripe_onboarding_complete",
            "documents",
            "created_at",
            "updated_at",
        ]

    def validate_commission_rate(self, value):
        if value < Decimal("0") or value > Decimal("100"):
            raise serializers.ValidationError("Commission rate must be between 0 and 100.")
        return value


class SupplierStatusActionSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=True, default="")
