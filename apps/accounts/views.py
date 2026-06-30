from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from . import services
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    TOTPLoginSerializer,
    TOTPVerifySerializer,
    UserProfileSerializer,
)


def _issue_token_pair(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": UserProfileSerializer(user).data,
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]

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
        return Response(_issue_token_pair(user), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

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
        if user.totp_enabled:
            session_token = services.create_totp_session(user)
            return Response(
                {"totp_required": True, "totp_session_token": session_token},
                status=status.HTTP_200_OK,
            )
        return Response(_issue_token_pair(user))


class TOTPLoginView(APIView):
    permission_classes = [AllowAny]

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
        return Response(_issue_token_pair(user))


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        try:
            token = RefreshToken(request.data.get("refresh", ""))
            token.blacklist()
        except (TokenError, Exception):
            pass  # Blacklisting is best-effort; short-lived access tokens expire naturally
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response(UserProfileSerializer(request.user).data)

    def patch(self, request: Request) -> Response:
        s = UserProfileSerializer(request.user, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

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
        request.user.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        s = PasswordResetRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.request_password_reset(s.validated_data["email"])
        return Response({"message": "If an account exists with that email, a reset link has been sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

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

    def get(self, request: Request) -> Response:
        uri = services.setup_totp(request.user)
        return Response({"otpauth_uri": uri})


class TOTPEnableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        s = TOTPVerifySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if not services.enable_totp(request.user, s.validated_data["code"]):
            return Response(
                {"error": {"code": "INVALID_TOTP", "message": "Invalid authenticator code."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"totp_enabled": True})


class TOTPDisableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        s = TOTPVerifySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if not services.disable_totp(request.user, s.validated_data["code"]):
            return Response(
                {"error": {"code": "INVALID_TOTP", "message": "Invalid authenticator code."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"totp_enabled": False})
