from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    # Registration and login
    path("register/", views.RegisterView.as_view(), name="auth-register"),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("login/totp/", views.TOTPLoginView.as_view(), name="auth-login-totp"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    # Password management
    path("password-reset/", views.PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path(
        "password-reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path("change-password/", views.ChangePasswordView.as_view(), name="auth-change-password"),
    # Two-factor authentication
    path("totp/setup/", views.TOTPSetupView.as_view(), name="auth-totp-setup"),
    path("totp/enable/", views.TOTPEnableView.as_view(), name="auth-totp-enable"),
    path("totp/disable/", views.TOTPDisableView.as_view(), name="auth-totp-disable"),
    # User profile
    path("me/", views.UserProfileView.as_view(), name="auth-me"),
    # Address book
    path("addresses/", views.AddressListCreateView.as_view(), name="address-list"),
    path("addresses/<uuid:pk>/", views.AddressDetailView.as_view(), name="address-detail"),
    path(
        "addresses/<uuid:pk>/default/",
        views.AddressSetDefaultView.as_view(),
        name="address-set-default",
    ),
    # Admin
    path("admin/users/", views.AdminUserListView.as_view(), name="admin-user-list"),
    path(
        "admin/users/<uuid:user_id>/unlock/",
        views.AdminUnlockUserView.as_view(),
        name="admin-user-unlock",
    ),
    path(
        "admin/users/<uuid:user_id>/suspend/",
        views.AdminSuspendUserView.as_view(),
        name="admin-user-suspend",
    ),
    path(
        "admin/users/<uuid:user_id>/activate/",
        views.AdminActivateUserView.as_view(),
        name="admin-user-activate",
    ),
    path(
        "admin/users/<uuid:user_id>/",
        views.AdminDeleteUserView.as_view(),
        name="admin-user-delete",
    ),
    path("admin/audit-log/", views.AdminAuditLogView.as_view(), name="admin-audit-log"),
]
