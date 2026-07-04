import hashlib

import pyotp
import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.accounts.models import PasswordResetToken
from apps.accounts.services import (
    MAX_LOGIN_ATTEMPTS,
    authenticate_user,
    confirm_password_reset,
    create_totp_session,
    disable_totp,
    enable_totp,
    register_user,
    request_password_reset,
    setup_totp,
    verify_totp_session,
)


@pytest.mark.django_db
class TestRegisterUser:
    def test_creates_user_with_correct_fields(self):
        user = register_user(
            "new@example.com", "Securepass123!", first_name="Jane", last_name="Doe"
        )
        assert user.email == "new@example.com"
        assert user.first_name == "Jane"
        assert user.check_password("Securepass123!")

    def test_email_lowercased(self):
        user = register_user("UPPER@EXAMPLE.COM", "Securepass123!")
        assert user.email == "upper@example.com"


@pytest.mark.django_db
class TestAuthenticateUser:
    def setup_method(self):
        cache.clear()

    def test_returns_user_on_valid_credentials(self, buyer):
        user, error = authenticate_user("buyer@example.com", "Securepass123!")
        assert user is not None
        assert error is None

    def test_returns_error_on_wrong_password(self, buyer):
        user, error = authenticate_user("buyer@example.com", "wrongpassword")
        assert user is None
        assert "Invalid credentials" in error

    def test_lockout_after_max_attempts(self, buyer):
        for _ in range(MAX_LOGIN_ATTEMPTS):
            authenticate_user("buyer@example.com", "wrong")
        user, error = authenticate_user("buyer@example.com", "Securepass123!")
        assert user is None
        assert "locked" in error.lower()

    def test_clears_attempts_on_success(self, buyer):
        authenticate_user("buyer@example.com", "wrong")
        user, error = authenticate_user("buyer@example.com", "Securepass123!")
        assert user is not None
        assert error is None


@pytest.mark.django_db
class TestTOTPFlow:
    def setup_method(self):
        cache.clear()

    def test_setup_returns_otpauth_uri(self, buyer):
        uri = setup_totp(buyer)
        assert uri.startswith("otpauth://totp/")
        assert "Provena" in uri

    def test_enable_with_valid_code(self, buyer):
        setup_totp(buyer)
        buyer.refresh_from_db()
        valid_code = pyotp.TOTP(buyer.totp_secret).now()
        result = enable_totp(buyer, valid_code)
        assert result is True
        buyer.refresh_from_db()
        assert buyer.totp_enabled is True

    def test_enable_with_invalid_code(self, buyer):
        setup_totp(buyer)
        result = enable_totp(buyer, "000000")
        assert result is False

    def test_disable_with_valid_code(self, buyer):
        setup_totp(buyer)
        buyer.refresh_from_db()
        valid_code = pyotp.TOTP(buyer.totp_secret).now()
        enable_totp(buyer, valid_code)
        buyer.refresh_from_db()
        valid_code2 = pyotp.TOTP(buyer.totp_secret).now()
        result = disable_totp(buyer, valid_code2)
        assert result is True
        buyer.refresh_from_db()
        assert buyer.totp_enabled is False
        assert buyer.totp_secret == ""

    def test_totp_session_flow(self, buyer):
        setup_totp(buyer)
        buyer.refresh_from_db()
        enable_totp(buyer, pyotp.TOTP(buyer.totp_secret).now())
        buyer.refresh_from_db()

        session_token = create_totp_session(buyer)
        valid_code = pyotp.TOTP(buyer.totp_secret).now()
        user, error = verify_totp_session(session_token, valid_code)
        assert user is not None
        assert error is None

    def test_totp_session_expired(self, buyer):
        user, error = verify_totp_session("nonexistent-token", "123456")
        assert user is None
        assert "expired" in error.lower()


@pytest.mark.django_db
class TestPasswordReset:
    def test_request_with_unknown_email_is_silent(self):
        request_password_reset("nobody@example.com")
        assert PasswordResetToken.objects.count() == 0

    def test_request_creates_token(self, buyer):
        request_password_reset("buyer@example.com")
        assert PasswordResetToken.objects.filter(user=buyer).count() == 1

    def test_request_invalidates_existing_tokens(self, buyer):
        request_password_reset("buyer@example.com")
        request_password_reset("buyer@example.com")
        # First token should be marked used
        tokens = PasswordResetToken.objects.filter(user=buyer).order_by("created_at")
        assert tokens[0].used_at is not None
        assert tokens[1].used_at is None

    def test_confirm_resets_password(self, buyer):
        import secrets

        raw_token = secrets.token_urlsafe(48)
        PasswordResetToken.objects.create(
            user=buyer,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        success, _error = confirm_password_reset(raw_token, "NewSecurepass456!")
        assert success is True
        buyer.refresh_from_db()
        assert buyer.check_password("NewSecurepass456!")

    def test_confirm_with_invalid_token(self):
        success, error = confirm_password_reset("invalid-token", "NewSecurepass456!")
        assert success is False
        assert "Invalid" in error

    def test_confirm_marks_token_used(self, buyer):
        import secrets

        raw_token = secrets.token_urlsafe(48)
        token_obj = PasswordResetToken.objects.create(
            user=buyer,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        confirm_password_reset(raw_token, "NewSecurepass456!")
        token_obj.refresh_from_db()
        assert token_obj.used_at is not None

    def test_confirm_token_cannot_be_reused(self, buyer):
        import secrets

        raw_token = secrets.token_urlsafe(48)
        PasswordResetToken.objects.create(
            user=buyer,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )
        confirm_password_reset(raw_token, "NewSecurepass456!")
        success, _ = confirm_password_reset(raw_token, "AnotherPass789!")
        assert success is False
