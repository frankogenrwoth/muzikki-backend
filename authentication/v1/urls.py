from django.urls import path
from .views import (
    SignupView,
    LoginView,
    RefreshView,
    LogoutView,
    ForgotPasswordView,
    ResetPasswordView,
    ActivateAccountView,
    UpdateProfileView,
)

urlpatterns = [
    path("signup/", SignupView.as_view(), name="auth-signup"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="auth-reset-password"),
    path("activate/", ActivateAccountView.as_view(), name="auth-activate"),
    path("update-profile/", UpdateProfileView.as_view(), name="auth-update-profile"),
]
