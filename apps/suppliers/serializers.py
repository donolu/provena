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
        ]


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
            "stripe_onboarding_complete",
            "documents",
            "created_at",
        ]

    def validate_business_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Business name cannot be blank.")
        return value.strip()


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
