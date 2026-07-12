import hashlib
import logging
import secrets
from datetime import timedelta

import pyotp
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.utils import timezone

from .models import Address, PasswordResetToken, Role, User

logger = logging.getLogger(__name__)

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 30
TOTP_SESSION_TTL = 300  # 5 minutes


def _attempts_key(email: str) -> str:
    return f"login_attempts:{email.lower()}"


def _totp_session_key(token: str) -> str:
    return f"totp_session:{token}"


def register_user(
    email: str, password: str, first_name: str = "", last_name: str = "", role: str = Role.BUYER
) -> User:
    user = User.objects.create_user(
        email=email.lower(),
        password=password,
        first_name=first_name,
        last_name=last_name,
        role=role,
    )
    try:
        from apps.notifications.email_service import send_welcome

        send_welcome(user)
    except Exception:
        logger.exception("Failed to send welcome email to %s", email)
    return user


def authenticate_user(email: str, password: str) -> tuple[User | None, str | None]:
    """
    Returns (user, None) on success or (None, error_message) on failure.
    Caller must check user.totp_enabled and issue a totp_session_token if True.
    """
    key = _attempts_key(email)
    attempts = cache.get(key, 0)
    if attempts >= MAX_LOGIN_ATTEMPTS:
        return None, "Account temporarily locked. Try again in 30 minutes."

    user = authenticate(username=email.lower(), password=password)
    if user is None:
        new_count = attempts + 1
        cache.set(key, new_count, LOCKOUT_MINUTES * 60)
        remaining = MAX_LOGIN_ATTEMPTS - new_count
        if remaining > 0:
            return None, f"Invalid credentials. {remaining} attempt(s) remaining before lockout."
        return None, "Account temporarily locked. Try again in 30 minutes."

    cache.delete(key)
    return user, None


def unlock_user(user: User) -> None:
    cache.delete(_attempts_key(user.email))


def is_locked(user: User) -> bool:
    return bool(cache.get(_attempts_key(user.email), 0) >= MAX_LOGIN_ATTEMPTS)


def suspend_user(user: User) -> None:
    user.is_active = False
    user.save(update_fields=["is_active"])
    logger.info("User %s suspended", user.email)


def activate_user(user: User) -> None:
    user.is_active = True
    user.save(update_fields=["is_active"])
    logger.info("User %s activated", user.email)


def delete_user(user: User) -> None:
    email = user.email
    user.delete()
    logger.info("User %s deleted", email)


def create_totp_session(user: User) -> str:
    """Issue a short-lived token after password is verified but before TOTP check."""
    session_token = secrets.token_urlsafe(32)
    cache.set(_totp_session_key(session_token), str(user.pk), TOTP_SESSION_TTL)
    return session_token


def verify_totp_session(session_token: str, totp_code: str) -> tuple[User | None, str | None]:
    user_id = cache.get(_totp_session_key(session_token))
    if not user_id:
        return None, "TOTP session expired or invalid. Please log in again."
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None, "User not found."
    if not _verify_totp_code(user, totp_code):
        return None, "Invalid authenticator code."
    cache.delete(_totp_session_key(session_token))
    return user, None


def setup_totp(user: User) -> str:
    """Generate a TOTP secret and return the otpauth:// URI for QR code display."""
    secret = pyotp.random_base32()
    user.totp_secret = secret
    user.save(update_fields=["totp_secret"])
    return pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="Provena")


def enable_totp(user: User, code: str) -> bool:
    """Verify the first code from the authenticator app and mark TOTP as enabled."""
    if not _verify_totp_code(user, code):
        return False
    user.totp_enabled = True
    user.save(update_fields=["totp_enabled"])
    return True


def disable_totp(user: User, code: str) -> bool:
    """Verify a current code before disabling TOTP, then wipe the secret."""
    if not _verify_totp_code(user, code):
        return False
    user.totp_enabled = False
    user.totp_secret = ""  # nosec B105 - clearing secret on TOTP disable, not hardcoding
    user.save(update_fields=["totp_enabled", "totp_secret"])
    return True


def _verify_totp_code(user: User, code: str) -> bool:
    if not user.totp_secret:
        return False
    return pyotp.TOTP(user.totp_secret).verify(code, valid_window=1)


def request_password_reset(email: str) -> None:
    """Enqueue a password reset email. Always returns silently to prevent email enumeration."""
    try:
        user = User.objects.get(email=email.lower(), is_active=True)
    except User.DoesNotExist:
        return

    # Invalidate any live tokens for this user
    PasswordResetToken.objects.filter(user=user, used_at__isnull=True).update(
        used_at=timezone.now()
    )

    raw_token = secrets.token_urlsafe(48)
    PasswordResetToken.objects.create(
        user=user,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        expires_at=timezone.now() + timedelta(hours=1),
    )
    try:
        from django.conf import settings

        from apps.notifications.email_service import send_password_reset

        frontend = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        reset_url = f"{frontend}/reset-password?token={raw_token}"
        send_password_reset(user, reset_url)
    except Exception:
        logger.exception("Failed to send password reset email to %s", email)
    logger.info("Password reset token created for %s", email)


def confirm_password_reset(raw_token: str, new_password: str) -> tuple[bool, str]:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    try:
        token_obj = PasswordResetToken.objects.select_related("user").get(
            token_hash=token_hash,
            used_at__isnull=True,
            expires_at__gt=timezone.now(),
        )
    except PasswordResetToken.DoesNotExist:
        return False, "Invalid or expired reset token."

    token_obj.user.set_password(new_password)
    token_obj.user.save(update_fields=["password"])
    token_obj.used_at = timezone.now()
    token_obj.save(update_fields=["used_at"])
    return True, ""


# ---------------------------------------------------------------------------
# Address book
# ---------------------------------------------------------------------------


def create_address(user: User, make_default: bool = False, **kwargs: object) -> Address:
    if make_default or not user.addresses.exists():
        user.addresses.filter(is_default=True).update(is_default=False)
        kwargs["is_default"] = True
    return Address.objects.create(user=user, **kwargs)


def update_address(address: Address, **kwargs: object) -> Address:
    allowed = {"label", "full_name", "line1", "line2", "city", "postcode", "country"}
    for field, value in kwargs.items():
        if field in allowed:
            setattr(address, field, value)
    address.save()
    return address


def set_default_address(address: Address) -> Address:
    address.user.addresses.filter(is_default=True).update(is_default=False)
    address.is_default = True
    address.save(update_fields=["is_default", "updated_at"])
    return address


def delete_address(address: Address) -> None:
    was_default = address.is_default
    address.delete()
    if was_default:
        next_address = address.user.addresses.first()
        if next_address:
            next_address.is_default = True
            next_address.save(update_fields=["is_default", "updated_at"])


def erase_account(user: User, password: str, totp_code: str = "") -> tuple[bool, str]:
    """Anonymise a user's personal data and disable the account (GDPR erasure).

    Re-authenticates with the password (and TOTP when enabled). Order and payment
    records are retained under legal obligation but stripped of the user's
    directly identifying data; saved addresses and auth material are removed.
    """
    from rest_framework_simplejwt.token_blacklist.models import (
        BlacklistedToken,
        OutstandingToken,
    )

    if not user.check_password(password):
        return False, "Password is incorrect."
    if user.totp_enabled and not _verify_totp_code(user, totp_code):
        return False, "Invalid authentication code."

    # Revoke every outstanding refresh token so existing sessions cannot continue.
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)

    # Remove saved addresses (directly identifying).
    Address.objects.filter(user=user).delete()

    # Scrub the user record; the row itself is kept for order/payment integrity.
    user.email = f"deleted-{user.id}@deleted.invalid"
    user.first_name = ""
    user.last_name = ""
    user.totp_enabled = False
    user.totp_secret = ""  # nosec B105 - clearing secret on erasure, not hardcoding
    user.is_active = False
    user.erased_at = timezone.now()
    user.set_unusable_password()
    user.save(
        update_fields=[
            "email",
            "first_name",
            "last_name",
            "totp_enabled",
            "totp_secret",
            "is_active",
            "erased_at",
            "password",
            "updated_at",
        ]
    )
    logger.info("Account erased for user %s", user.id)
    return True, ""
