import pytest
from django.utils import timezone

from apps.accounts.models import PasswordResetToken, Role, User


@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self):
        user = User.objects.create_user(email="test@example.com", password="Securepass123!")
        assert user.email == "test@example.com"
        assert user.role == Role.BUYER
        assert user.is_active is True
        assert user.is_staff is False
        assert user.totp_enabled is False
        assert user.check_password("Securepass123!")

    def test_email_normalised_to_lowercase(self):
        user = User.objects.create_user(email="Test@Example.COM", password="Securepass123!")
        assert user.email == "test@example.com"

    def test_str_returns_email(self):
        user = User.objects.create_user(email="str@example.com", password="Securepass123!")
        assert str(user) == "str@example.com"

    def test_create_superuser_sets_admin_role(self):
        user = User.objects.create_superuser(email="admin@example.com", password="Securepass123!")
        assert user.role == Role.ADMIN
        assert user.is_staff is True
        assert user.is_superuser is True

    def test_create_user_without_email_raises(self):
        with pytest.raises(ValueError, match="Email is required"):
            User.objects.create_user(email="", password="Securepass123!")

    def test_uuid_primary_key(self):
        user = User.objects.create_user(email="uuid@example.com", password="Securepass123!")
        assert user.pk is not None
        assert len(str(user.pk)) == 36  # UUID4 format


@pytest.mark.django_db
class TestPasswordResetToken:
    def test_is_valid_for_unexpired_unused_token(self, buyer):
        token = PasswordResetToken.objects.create(
            user=buyer,
            token_hash="abc123",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        assert token.is_valid is True

    def test_is_invalid_after_use(self, buyer):
        token = PasswordResetToken.objects.create(
            user=buyer,
            token_hash="def456",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
            used_at=timezone.now(),
        )
        assert token.is_valid is False

    def test_str_includes_email(self, buyer):
        token = PasswordResetToken.objects.create(
            user=buyer,
            token_hash="ghi789",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        assert buyer.email in str(token)
