from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Address, DataExportRequest, User


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=12)
    password_confirm = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150, default="", allow_blank=True)
    last_name = serializers.CharField(max_length=150, default="", allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.lower()

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})  # nosec B105
        validate_password(data["password"])
        return data


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class TOTPLoginSerializer(serializers.Serializer):
    totp_session_token = serializers.CharField()
    totp_code = serializers.CharField(min_length=6, max_length=6)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role", "totp_enabled", "created_at"]
        read_only_fields = ["id", "email", "role", "totp_enabled", "created_at"]


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=12)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})  # nosec B105
        validate_password(data["new_password"])
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=12)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})  # nosec B105
        validate_password(data["new_password"])
        return data


class TOTPVerifySerializer(serializers.Serializer):
    code = serializers.CharField(min_length=6, max_length=6)


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "is_staff",
            "totp_enabled",
            "created_at",
        ]
        read_only_fields = fields


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id",
            "label",
            "full_name",
            "line1",
            "line2",
            "city",
            "postcode",
            "country",
            "is_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_default", "created_at", "updated_at"]


class AddressWriteSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=100, allow_blank=True, default="")  # type: ignore[assignment]
    full_name = serializers.CharField(max_length=200)
    line1 = serializers.CharField(max_length=200)
    line2 = serializers.CharField(max_length=200, allow_blank=True, default="")
    city = serializers.CharField(max_length=100)
    postcode = serializers.CharField(max_length=20)
    country = serializers.CharField(max_length=2, default="GB")

    def validate_full_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Full name cannot be blank.")
        return value.strip()

    def validate_line1(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Address line 1 cannot be blank.")
        return value.strip()

    def validate_postcode(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Postcode cannot be blank.")
        return value.strip().upper()

    def validate_country(self, value: str) -> str:
        if len(value) != 2:
            raise serializers.ValidationError("Country must be a 2-letter ISO code.")
        return value.upper()


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.SerializerMethodField()

    def get_actor_email(self, obj) -> str | None:
        return obj.actor.email if obj.actor else None

    class Meta:
        from apps.accounts.models import AuditLog

        model = AuditLog
        fields = [
            "id",
            "actor_email",
            "action",
            "target_type",
            "target_id",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class DataExportRequestSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = DataExportRequest
        fields = [
            "id",
            "user_email",
            "status",
            "requested_at",
            "completed_at",
            "expires_at",
        ]
        read_only_fields = fields


class AccountDeletionSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    totp_code = serializers.CharField(required=False, allow_blank=True, default="")
