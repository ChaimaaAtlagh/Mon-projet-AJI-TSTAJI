from django.urls import path

from core.views import (
    AdminUserListView,
    DocumentDownloadView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
)
from core.auth_views import LoginView, LogoutView, RefreshView, RegisterView
from core.assistant_views import AssistantChatView


urlpatterns = [
    path("me", MeView.as_view(), name="me"),
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/register", RegisterView.as_view(), name="auth-register"),
    path("auth/refresh", RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("auth/password-reset", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path(
        "auth/password-reset/confirm",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("assistant/chat", AssistantChatView.as_view(), name="assistant-chat"),
    path("admin/users", AdminUserListView.as_view(), name="admin-users"),
    path(
        "me/documents/<uuid:document_id>/download",
        DocumentDownloadView.as_view(),
        name="document-download",
    ),
]

