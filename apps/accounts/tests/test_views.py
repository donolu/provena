import pyotp
import pytest
from django.urls import reverse
from rest_framework import status

from apps.accounts.models import User
from apps.accounts.services import setup_totp, enable_totp


REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
TOTP_LOGIN_URL = "/api/v1/auth/login/totp/"
LOGOUT_URL = "/api/v1/auth/logout/"
ME_URL = "/api/v1/auth/me/"
CHANGE_PASSWORD_URL = "/api/v1/auth/change-password/"
PASSWORD_RESET_URL = "/api/v1/auth/password-reset/"
PASSWORD_RESET_CONFIRM_URL = "/api/v1/auth/password-reset/confirm/"
TOTP_SETUP_URL = "/api/v1/auth/totp/setup/"
TOTP_ENABLE_URL = "/api/v1/auth/totp/enable/"
TOTP_DISABLE_URL = "/api/v1/auth/totp/disable/"


@pytest.mark.django_db
class TestRegisterView:
    def test_register_returns_tokens_and_user(self, api_client):
        res = api_client.post(REGISTER_URL, {
            "email": "newuser@example.com",
            "password": "Securepass123!",
            "password_confirm": "Securepass123!",
            "first_name": "New",
            "last_name": "User",
        })
        assert res.status_code == status.HTTP_201_CREATED
        assert "access" in res.data
        assert "refresh" in res.data
        assert res.data["user"]["email"] == "newuser@example.com"

    def test_register_duplicate_email_returns_400(self, api_client, buyer):
        res = api_client.post(REGISTER_URL, {
            "email": "buyer@example.com",
            "password": "Securepass123!",
            "password_confirm": "Securepass123!",
        })
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_mismatched_passwords_returns_400(self, api_client):
        res = api_client.post(REGISTER_URL, {
            "email": "new@example.com",
            "password": "Securepass123!",
            "password_confirm": "Different456!",
        })
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_weak_password_returns_400(self, api_client):
        res = api_client.post(REGISTER_URL, {
            "email": "weak@example.com",
            "password": "password",
            "password_confirm": "password",
        })
        assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLoginView:
    def setup_method(self):
        from django.core.cache import cache
        cache.clear()

    def test_login_returns_tokens(self, api_client, buyer):
        res = api_client.post(LOGIN_URL, {"email": "buyer@example.com", "password": "Securepass123!"})
        assert res.status_code == status.HTTP_200_OK
        assert "access" in res.data
        assert "refresh" in res.data

    def test_login_wrong_password_returns_401(self, api_client, buyer):
        res = api_client.post(LOGIN_URL, {"email": "buyer@example.com", "password": "wrongpass"})
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_with_totp_enabled_returns_session_token(self, api_client, buyer):
        setup_totp(buyer)
        buyer.refresh_from_db()
        enable_totp(buyer, pyotp.TOTP(buyer.totp_secret).now())
        res = api_client.post(LOGIN_URL, {"email": "buyer@example.com", "password": "Securepass123!"})
        assert res.status_code == status.HTTP_200_OK
        assert res.data["totp_required"] is True
        assert "totp_session_token" in res.data
        assert "access" not in res.data


@pytest.mark.django_db
class TestTOTPLoginView:
    def setup_method(self):
        from django.core.cache import cache
        cache.clear()

    def test_totp_login_completes_authentication(self, api_client, buyer):
        setup_totp(buyer)
        buyer.refresh_from_db()
        enable_totp(buyer, pyotp.TOTP(buyer.totp_secret).now())
        buyer.refresh_from_db()

        # Step 1: get session token
        res = api_client.post(LOGIN_URL, {"email": "buyer@example.com", "password": "Securepass123!"})
        session_token = res.data["totp_session_token"]

        # Step 2: complete with TOTP code
        res2 = api_client.post(TOTP_LOGIN_URL, {
            "totp_session_token": session_token,
            "totp_code": pyotp.TOTP(buyer.totp_secret).now(),
        })
        assert res2.status_code == status.HTTP_200_OK
        assert "access" in res2.data

    def test_totp_login_with_invalid_code_returns_401(self, api_client, buyer):
        setup_totp(buyer)
        buyer.refresh_from_db()
        enable_totp(buyer, pyotp.TOTP(buyer.totp_secret).now())
        res = api_client.post(LOGIN_URL, {"email": "buyer@example.com", "password": "Securepass123!"})
        session_token = res.data["totp_session_token"]

        res2 = api_client.post(TOTP_LOGIN_URL, {
            "totp_session_token": session_token,
            "totp_code": "000000",
        })
        assert res2.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserProfileView:
    def test_get_profile_returns_user_data(self, buyer_client, buyer):
        res = buyer_client.get(ME_URL)
        assert res.status_code == status.HTTP_200_OK
        assert res.data["email"] == buyer.email
        assert res.data["role"] == "BUYER"

    def test_unauthenticated_returns_401(self, api_client):
        res = api_client.get(ME_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_patch_updates_name(self, buyer_client, buyer):
        res = buyer_client.patch(ME_URL, {"first_name": "Updated"})
        assert res.status_code == status.HTTP_200_OK
        assert res.data["first_name"] == "Updated"

    def test_patch_cannot_change_role(self, buyer_client):
        res = buyer_client.patch(ME_URL, {"role": "ADMIN"})
        assert res.status_code == status.HTTP_200_OK
        assert res.data["role"] == "BUYER"


@pytest.mark.django_db
class TestChangePasswordView:
    def test_change_password_succeeds(self, buyer_client, buyer):
        res = buyer_client.post(CHANGE_PASSWORD_URL, {
            "current_password": "Securepass123!",
            "new_password": "NewSecurepass456!",
            "new_password_confirm": "NewSecurepass456!",
        })
        assert res.status_code == status.HTTP_204_NO_CONTENT
        buyer.refresh_from_db()
        assert buyer.check_password("NewSecurepass456!")

    def test_wrong_current_password_returns_400(self, buyer_client):
        res = buyer_client.post(CHANGE_PASSWORD_URL, {
            "current_password": "wrongpassword",
            "new_password": "NewSecurepass456!",
            "new_password_confirm": "NewSecurepass456!",
        })
        assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestPasswordResetViews:
    def test_reset_request_always_returns_200(self, api_client):
        res = api_client.post(PASSWORD_RESET_URL, {"email": "nobody@example.com"})
        assert res.status_code == status.HTTP_200_OK

    def test_reset_confirm_with_invalid_token_returns_400(self, api_client):
        res = api_client.post(PASSWORD_RESET_CONFIRM_URL, {
            "token": "invalid-token",
            "new_password": "NewSecurepass456!",
            "new_password_confirm": "NewSecurepass456!",
        })
        assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTOTPManagementViews:
    def test_setup_returns_otpauth_uri(self, buyer_client):
        res = buyer_client.get(TOTP_SETUP_URL)
        assert res.status_code == status.HTTP_200_OK
        assert res.data["otpauth_uri"].startswith("otpauth://totp/")

    def test_enable_with_valid_code(self, buyer_client, buyer):
        buyer_client.get(TOTP_SETUP_URL)
        buyer.refresh_from_db()
        valid_code = pyotp.TOTP(buyer.totp_secret).now()
        res = buyer_client.post(TOTP_ENABLE_URL, {"code": valid_code})
        assert res.status_code == status.HTTP_200_OK
        assert res.data["totp_enabled"] is True

    def test_enable_with_invalid_code_returns_400(self, buyer_client, buyer):
        buyer_client.get(TOTP_SETUP_URL)
        res = buyer_client.post(TOTP_ENABLE_URL, {"code": "000000"})
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_disable_totp(self, buyer_client, buyer):
        buyer_client.get(TOTP_SETUP_URL)
        buyer.refresh_from_db()
        enable_code = pyotp.TOTP(buyer.totp_secret).now()
        buyer_client.post(TOTP_ENABLE_URL, {"code": enable_code})
        buyer.refresh_from_db()
        disable_code = pyotp.TOTP(buyer.totp_secret).now()
        res = buyer_client.post(TOTP_DISABLE_URL, {"code": disable_code})
        assert res.status_code == status.HTTP_200_OK
        assert res.data["totp_enabled"] is False
