import hashlib
import logging
import secrets
from datetime import timedelta

import pyotp
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.utils import timezone

from .models import PasswordResetToken, Role, User

logger = logging.getLogger(__name__)

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 30
TOTP_SESSION_TTL = 300  # 5 minutes


def _attempts_key(email: str) -> str:
    return f"login_attempts:{email.lower()}"


def _totp_session_key(token: str) -> str:
    return f"totp_session:{token}"


def register_user(email: str, password: str, first_name: str = "", last_name: str = "", role: str = Role.BUYER) -> User:
    return User.objects.create_user(
        email=email.lower(),
        password=password,
        first_name=first_name,
        last_name=last_name,
        role=role,
    )


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
    user.totp_secret = ""
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
    PasswordResetToken.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())

    raw_token = secrets.token_urlsafe(48)
    PasswordResetToken.objects.create(
        user=user,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        expires_at=timezone.now() + timedelta(hours=1),
    )
    # TODO: send email via notifications.services.send() once that app is built
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
