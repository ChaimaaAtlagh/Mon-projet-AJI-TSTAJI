from datetime import timedelta
import hashlib

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Role, User, UserRole, UserSession


class RolePermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_role = Role.objects.create(code=Role.Code.USER, name="User")
        self.admin_role = Role.objects.create(code=Role.Code.ADMIN, name="Admin")
        self.user = User.objects.create_user("user@example.com", "Fictive-Test-Password-123!")
        self.admin = User.objects.create_user("admin@example.com", "Fictive-Test-Password-123!")
        UserRole.objects.create(user=self.user, role=self.user_role)
        UserRole.objects.create(user=self.admin, role=self.admin_role)

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, 401)

    def test_regular_user_can_read_only_me(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "user@example.com")
        self.assertNotIn("password", response.data)
        self.assertNotIn("password_hash", response.data)

    def test_regular_user_cannot_list_all_users(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("admin-users"))
        self.assertEqual(response.status_code, 403)

    def test_admin_role_can_list_users_without_password_fields(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse("admin-users"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        serialized = str(response.data)
        self.assertNotIn("password_hash", serialized)
        self.assertNotIn("access_token_hash", serialized)

    def test_suspended_user_cannot_read_me(self):
        self.user.status = User.Status.SUSPENDED
        self.user.save(update_fields=("status",))
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, 403)

    def test_bearer_session_authentication_accepts_only_valid_hash(self):
        token = "fictional-test-access-token"
        UserSession.objects.create(
            user=self.user,
            access_token_hash=hashlib.sha256(token.encode()).hexdigest(),
            access_expires_at=timezone.now() + timedelta(minutes=5),
            refresh_token_hash=hashlib.sha256(b"fictional-refresh-token").hexdigest(),
            refresh_expires_at=timezone.now() + timedelta(days=1),
        )
        response = self.client.get(
            reverse("me"),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 200)

    def test_revoked_bearer_session_is_rejected(self):
        token = "fictional-revoked-access-token"
        UserSession.objects.create(
            user=self.user,
            access_token_hash=hashlib.sha256(token.encode()).hexdigest(),
            access_expires_at=timezone.now() + timedelta(minutes=5),
            refresh_token_hash=hashlib.sha256(b"fictional-revoked-refresh-token").hexdigest(),
            refresh_expires_at=timezone.now() + timedelta(days=1),
            revoked_at=timezone.now(),
        )
        response = self.client.get(
            reverse("me"),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 401)

