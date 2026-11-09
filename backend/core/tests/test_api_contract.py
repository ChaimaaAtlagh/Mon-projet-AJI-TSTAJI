from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from core.models import Profile, Role, User, UserRole


class MinimalContractTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user("admin@example.com", "Fictive-Test-Password-123!")
        self.user = User.objects.create_user("fictive.user@example.com", "Fictive-Test-Password-123!")
        Profile.objects.create(user=self.user, first_name="Fictive", last_name="Person")
        role = Role.objects.create(code=Role.Code.ADMIN, name="Admin")
        UserRole.objects.create(user=self.admin, role=role)

    def test_admin_user_list_is_paginated_and_safe(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse("admin-users"), {"page": 1, "page_size": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {"count", "next", "previous", "results"})
        self.assertEqual(len(response.data["results"]), 1)
        result = response.data["results"][0]
        self.assertNotIn("password", result)
        self.assertNotIn("password_hash", result)
        self.assertNotIn("legacy_cv_path", result)

