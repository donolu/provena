from django.conf import settings
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.audit import audit_action
from apps.pagination import PaginatedListMixin

from . import services
from .models import User
from .serializers import (
    AddressSerializer,
    AddressWriteSerializer,
    AdminUserSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    TOTPLoginSerializer,
    TOTPVerifySerializer,
    UserProfileSerializer,
)

_COOKIE_PATH = "/api/v1/auth/"


def _set_refresh_cookie(response: Response, token: str) -> None:
    max_age = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=token,
        max_age=max_age,
        path=_COOKIE_PATH,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=_COOKIE_PATH,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )


def _auth_response(user: User, http_status: int = status.HTTP_200_OK) -> Response:
    """Build a login/register response: access token in body, refresh token in HttpOnly cookie."""
    refresh = RefreshToken.for_user(user)
    response = Response(
        {"access": str(refresh.access_token), "user": UserProfileSerializer(user).data},
        status=http_status,
    )
    _set_refresh_cookie(response, str(refresh))
    return response


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Register a new user",
        description="Creates a buyer account and returns a JWT token pair. "
        "Password must be at least 12 characters.",
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(description="JWT access/refresh tokens and user profile"),
            400: OpenApiResponse(description="Validation error (duplicate email, weak password)"),
        },
    )
    def post(self, request: Request) -> Response:
        s = RegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        user = services.register_user(
            email=d["email"],
            password=d["password"],
            first_name=d.get("first_name", ""),
            last_name=d.get("last_name", ""),
        )
        return _auth_response(user, status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Log in",
        description="Authenticates with email and password. "
        "If TOTP is enabled the response contains `totp_required: true` and a "
        "`totp_session_token`; submit that token with the 6-digit code to "
        "`POST /api/v1/auth/login/totp/` to complete login. "
        "Accounts are locked for 30 minutes after 5 failed attempts.",
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                description="JWT token pair, OR `{totp_required: true, totp_session_token}` "
                "when TOTP is enabled"
            ),
            401: OpenApiResponse(description="Invalid credentials or account locked"),
        },
    )
    def post(self, request: Request) -> Response:
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        user, error = services.authenticate_user(d["email"], d["password"])
        if error:
            return Response(
                {"error": {"code": "AUTH_FAILED", "message": error}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if user.totp_enabled:  # type: ignore[union-attr]
            session_token = services.create_totp_session(user)  # type: ignore[arg-type]
            return Response(
                {"totp_required": True, "totp_session_token": session_token},
                status=status.HTTP_200_OK,
            )
        return _auth_response(user)


class TOTPLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Complete TOTP login",
        description="Second step of the TOTP two-factor login flow. "
        "Submit the `totp_session_token` from the initial login response alongside "
        "the 6-digit TOTP code from the authenticator app. "
        "The session token is single-use and expires after 5 minutes.",
        request=TOTPLoginSerializer,
        responses={
            200: OpenApiResponse(description="JWT access/refresh tokens and user profile"),
            401: OpenApiResponse(
                description="Invalid or expired session token, or wrong TOTP code"
            ),
        },
    )
    def post(self, request: Request) -> Response:
        s = TOTPLoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        user, error = services.verify_totp_session(d["totp_session_token"], d["totp_code"])
        if error:
            return Response(
                {"error": {"code": "TOTP_FAILED", "message": error}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return _auth_response(user)


class CookieTokenRefreshView(APIView):
    """Refresh the access token using the HttpOnly refresh-token cookie."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Refresh access token",
        description="Reads the refresh token from the `provena_rt` HttpOnly cookie, "
        "issues a new short-lived access token, and rotates the refresh token cookie.",
        request=None,
        responses={
            200: OpenApiResponse(description="`{access: '...'}`"),
            401: OpenApiResponse(description="Cookie missing or token invalid/expired"),
        },
    )
    def post(self, request: Request) -> Response:
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not raw:
            return Response(
                {"error": {"code": "NO_REFRESH_TOKEN", "message": "Refresh token not found."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            refresh = RefreshToken(raw)
        except TokenError:
            return Response(
                {"error": {"code": "INVALID_TOKEN", "message": "Token is invalid or expired."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        new_access = str(refresh.access_token)
        new_refresh = raw

        if jwt_settings.ROTATE_REFRESH_TOKENS:
            if jwt_settings.BLACKLIST_AFTER_ROTATION:
                refresh.blacklist()
            refresh.set_jti()
            refresh.set_exp()
            refresh.set_iat()
            new_refresh = str(refresh)

        response = Response({"access": new_access})
        _set_refresh_cookie(response, new_refresh)
        return response


class LogoutView(APIView):
    """Blacklist the refresh token cookie and clear it."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Log out",
        description="Reads the refresh token from the `provena_rt` HttpOnly cookie, "
        "blacklists it so it cannot be used again, and clears the cookie. "
        "The short-lived access token expires naturally after 15 minutes. "
        "Returns 204 regardless of whether a cookie was present.",
        request=None,
        responses={204: OpenApiResponse(description="Logged out")},
    )
    def post(self, request: Request) -> Response:
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except (TokenError, Exception):  # noqa: S110
                pass  # Expired tokens don't need blacklisting
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _clear_refresh_cookie(response)
        return response


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["User Profile"],
        summary="Get current user profile",
        responses={200: UserProfileSerializer},
    )
    def get(self, request: Request) -> Response:
        return Response(UserProfileSerializer(request.user).data)

    @extend_schema(
        tags=["User Profile"],
        summary="Update current user profile",
        description="Partial update: only include fields you want to change. "
        "Email and role cannot be changed via this endpoint.",
        request=UserProfileSerializer,
        responses={
            200: UserProfileSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def patch(self, request: Request) -> Response:
        s = UserProfileSerializer(request.user, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["User Profile"],
        summary="Change password",
        description="Requires the current password for verification. "
        "New password must meet the same strength requirements as registration.",
        request=ChangePasswordSerializer,
        responses={
            204: OpenApiResponse(description="Password changed"),
            400: OpenApiResponse(description="Current password incorrect or new password too weak"),
        },
    )
    def post(self, request: Request) -> Response:
        s = ChangePasswordSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        if not request.user.check_password(d["current_password"]):
            return Response(
                {"error": {"code": "WRONG_PASSWORD", "message": "Current password is incorrect."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.set_password(d["new_password"])
        request.user.save(update_fields=["password"])  # type: ignore[call-arg]
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Password Reset"],
        summary="Request a password reset email",
        description="Sends a password reset link to the supplied email address. "
        "Always returns 200 — no indication is given whether the email exists "
        "(prevents user enumeration).",
        request=PasswordResetRequestSerializer,
        responses={200: OpenApiResponse(description="Reset email sent (if account exists)")},
    )
    def post(self, request: Request) -> Response:
        s = PasswordResetRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.request_password_reset(s.validated_data["email"])
        return Response(
            {"message": "If an account exists with that email, a reset link has been sent."}
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Password Reset"],
        summary="Confirm password reset",
        description="Consumes the single-use token from the reset email and sets a new password. "
        "Tokens expire after 1 hour.",
        request=PasswordResetConfirmSerializer,
        responses={
            204: OpenApiResponse(description="Password reset successful"),
            400: OpenApiResponse(description="Token invalid, expired, or already used"),
        },
    )
    def post(self, request: Request) -> Response:
        s = PasswordResetConfirmSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        success, error = services.confirm_password_reset(d["token"], d["new_password"])
        if not success:
            return Response(
                {"error": {"code": "INVALID_TOKEN", "message": error}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class TOTPSetupView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Two-Factor Authentication"],
        summary="Get TOTP setup URI",
        description="Returns an `otpauth://` URI that can be rendered as a QR code for scanning "
        "with an authenticator app (Google Authenticator, Authy, etc.). "
        "After scanning, verify the setup by calling `POST /api/v1/auth/totp/enable/`.",
        responses={
            200: OpenApiResponse(description="`{otpauth_uri: 'otpauth://totp/...'}`"),
        },
    )
    def get(self, request: Request) -> Response:
        uri = services.setup_totp(request.user)  # type: ignore[arg-type]
        return Response({"otpauth_uri": uri})


class TOTPEnableView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Two-Factor Authentication"],
        summary="Enable TOTP",
        description="Verifies a code from the authenticator app and marks TOTP as enabled. "
        "Must be called after `GET /api/v1/auth/totp/setup/`.",
        request=TOTPVerifySerializer,
        responses={
            200: OpenApiResponse(description="`{totp_enabled: true}`"),
            400: OpenApiResponse(description="Invalid TOTP code"),
        },
    )
    def post(self, request: Request) -> Response:
        s = TOTPVerifySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if not services.enable_totp(request.user, s.validated_data["code"]):  # type: ignore[arg-type]
            return Response(
                {"error": {"code": "INVALID_TOTP", "message": "Invalid authenticator code."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"totp_enabled": True})


class AdminUnlockUserView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["User Profile"],
        summary="Unlock a locked account (admin)",
        description="Clears the failed-login attempt counter for a user, allowing them to log in again immediately.",
        responses={200: OpenApiResponse(description="`{unlocked: true}`")},
    )
    def post(self, request: Request, user_id: str) -> Response:
        from .models import User

        user = get_object_or_404(User, id=user_id)
        was_locked = services.is_locked(user)
        services.unlock_user(user)
        return Response({"unlocked": True, "was_locked": was_locked})


class TOTPDisableView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Two-Factor Authentication"],
        summary="Disable TOTP",
        description="Requires a valid TOTP code as confirmation before disabling two-factor authentication.",
        request=TOTPVerifySerializer,
        responses={
            200: OpenApiResponse(description="`{totp_enabled: false}`"),
            400: OpenApiResponse(description="Invalid TOTP code"),
        },
    )
    def post(self, request: Request) -> Response:
        s = TOTPVerifySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if not services.disable_totp(request.user, s.validated_data["code"]):  # type: ignore[arg-type]
            return Response(
                {"error": {"code": "INVALID_TOTP", "message": "Invalid authenticator code."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"totp_enabled": False})


class AdminUserListView(PaginatedListMixin, APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Admin: Users"],
        summary="List all users",
        responses={200: AdminUserSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        qs = User.objects.order_by("-created_at")
        if role := request.query_params.get("role"):
            qs = qs.filter(role=role)
        if active := request.query_params.get("is_active"):
            qs = qs.filter(is_active=active.lower() in ("1", "true", "yes"))
        if q := request.query_params.get("q"):
            from django.db.models import Q as DQ

            qs = qs.filter(
                DQ(email__icontains=q) | DQ(first_name__icontains=q) | DQ(last_name__icontains=q)
            )
        return self.paginate(qs, AdminUserSerializer, request)


class AdminSuspendUserView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Admin: Users"],
        summary="Suspend a user account",
        responses={200: AdminUserSerializer},
    )
    @audit_action(
        "user.suspended", target_type="User", get_target_id=lambda req, kw: kw.get("user_id")
    )
    def post(self, request: Request, user_id: str) -> Response:
        user = get_object_or_404(User, id=user_id)
        if user == request.user:
            return Response(
                {"detail": "Cannot suspend your own account."}, status=status.HTTP_400_BAD_REQUEST
            )
        if user.is_staff:
            return Response(
                {"detail": "Cannot suspend a staff account."}, status=status.HTTP_400_BAD_REQUEST
            )
        services.suspend_user(user)
        return Response(AdminUserSerializer(user).data)


class AdminActivateUserView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Admin: Users"],
        summary="Re-activate a suspended user account",
        responses={200: AdminUserSerializer},
    )
    @audit_action(
        "user.activated", target_type="User", get_target_id=lambda req, kw: kw.get("user_id")
    )
    def post(self, request: Request, user_id: str) -> Response:
        user = get_object_or_404(User, id=user_id)
        services.activate_user(user)
        return Response(AdminUserSerializer(user).data)


class AdminDeleteUserView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Admin: Users"],
        summary="Delete a user account",
        responses={204: OpenApiResponse(description="Deleted")},
    )
    def delete(self, request: Request, user_id: str) -> Response:
        user = get_object_or_404(User, id=user_id)
        if user == request.user:
            return Response(
                {"detail": "Cannot delete your own account."}, status=status.HTTP_400_BAD_REQUEST
            )
        if user.is_staff:
            return Response(
                {"detail": "Cannot delete a staff account."}, status=status.HTTP_400_BAD_REQUEST
            )
        services.delete_user(user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Address book
# ---------------------------------------------------------------------------


class AddressListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Accounts: Addresses"],
        summary="List saved addresses",
        responses={200: AddressSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        qs = request.user.addresses.all()  # type: ignore[union-attr]
        return Response(AddressSerializer(qs, many=True).data)

    @extend_schema(
        tags=["Accounts: Addresses"],
        summary="Save a new address",
        request=AddressWriteSerializer,
        responses={
            201: AddressSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def post(self, request: Request) -> Response:
        s = AddressWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        make_default = request.data.get("is_default", False)
        address = services.create_address(
            user=request.user,  # type: ignore[arg-type]
            make_default=bool(make_default),
            **s.validated_data,
        )
        return Response(AddressSerializer(address).data, status=status.HTTP_201_CREATED)


class AddressDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _own_address(self, request: Request, pk: str):
        return get_object_or_404(
            request.user.addresses,  # type: ignore[union-attr]
            pk=pk,
        )

    @extend_schema(
        tags=["Accounts: Addresses"],
        summary="Update a saved address",
        request=AddressWriteSerializer,
        responses={
            200: AddressSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Not found"),
        },
    )
    def patch(self, request: Request, pk: str) -> Response:
        address = self._own_address(request, pk)
        s = AddressWriteSerializer(address, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        address = services.update_address(address, **s.validated_data)
        return Response(AddressSerializer(address).data)

    @extend_schema(
        tags=["Accounts: Addresses"],
        summary="Delete a saved address",
        responses={
            204: OpenApiResponse(description="Deleted"),
            404: OpenApiResponse(description="Not found"),
        },
    )
    def delete(self, request: Request, pk: str) -> Response:
        address = self._own_address(request, pk)
        services.delete_address(address)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AddressSetDefaultView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Accounts: Addresses"],
        summary="Set address as default",
        request=None,
        responses={
            200: AddressSerializer,
            404: OpenApiResponse(description="Not found"),
        },
    )
    def post(self, request: Request, pk: str) -> Response:
        address = get_object_or_404(request.user.addresses, pk=pk)  # type: ignore[union-attr]
        address = services.set_default_address(address)
        return Response(AddressSerializer(address).data)


class AdminAuditLogView(PaginatedListMixin, APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Admin: Users"],
        summary="Admin audit log",
        description="Paginated list of admin actions (approve, suspend, refund, etc.) ordered newest first.",
    )
    def get(self, request: Request) -> Response:
        from apps.accounts.models import AuditLog
        from apps.accounts.serializers import AuditLogSerializer

        qs = AuditLog.objects.select_related("actor").order_by("-created_at")
        action_filter = request.query_params.get("action")
        if action_filter:
            qs = qs.filter(action__icontains=action_filter)
        return self.paginate(qs, AuditLogSerializer, request)
