import hashlib
import tempfile
from datetime import timedelta
from pathlib import Path

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    PasswordResetToken,
    Profile,
    Role,
    User,
    UserPreferences,
    UserRole,
    UserSession,
)


class AuthenticationApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            "person@example.com", "Original-Strong-Password-554!", display_name="Test Person"
        )

    def login(self, password="Original-Strong-Password-554!"):
        return self.client.post(
            reverse("auth-login"),
            {"email": self.user.email, "password": password},
            format="json",
        )

    def test_login_creates_hashed_opaque_session_and_bearer_token_works(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        access_token = response.data["access_token"]
        refresh_token = response.data["refresh_token"]
        session = UserSession.objects.get(user=self.user)
        self.assertEqual(session.access_token_hash, hashlib.sha256(access_token.encode()).hexdigest())
        self.assertEqual(session.refresh_token_hash, hashlib.sha256(refresh_token.encode()).hexdigest())
        self.assertNotIn(access_token, session.access_token_hash)
        self.assertNotIn(refresh_token, session.refresh_token_hash)
        self.assertNotIn("password", response.data["user"])

        me = self.client.get(reverse("me"), HTTP_AUTHORIZATION=f"Bearer {access_token}")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["email"], self.user.email)

    def test_invalid_password_and_suspended_account_return_same_generic_error(self):
        wrong = self.login("Incorrect-Strong-Password-554!")
        self.user.status = User.Status.SUSPENDED
        self.user.save(update_fields=("status",))
        suspended = self.login()
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(suspended.status_code, 401)
        self.assertEqual(wrong.data, suspended.data)
        self.assertEqual(UserSession.objects.count(), 0)

    def test_register_creates_argon2_user_profile_preferences_role_and_session(self):
        response = self.client.post(
            reverse("auth-register"),
            {
                "email": "new.person@example.com",
                "password": "New-Strong-Password-881!",
                "display_name": "New Person",
                "phone": "0600000000",
                "city": "Marrakech",
                "institution": "Établissement fictif",
                "sector": "Informatique",
                "diploma": "Technicien",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        created = User.objects.get(email_normalized="new.person@example.com")
        self.assertTrue(created.check_password("New-Strong-Password-881!"))
        self.assertEqual(created.password_scheme, User.PasswordScheme.ARGON2ID)
        self.assertEqual(created.profile.phone, "0600000000")
        self.assertEqual(created.profile.institution, "Établissement fictif")
        self.assertTrue(UserPreferences.objects.filter(user=created).exists())
        self.assertTrue(
            UserRole.objects.filter(user=created, role__code=Role.Code.USER).exists()
        )
        self.assertNotIn("password", response.data)
        self.assertEqual(response.data["user"]["email"], created.email)

    def test_register_rejects_weak_or_duplicate_password_without_overwriting(self):
        weak = self.client.post(
            reverse("auth-register"),
            {"email": "weak@example.com", "password": "short", "display_name": "Weak"},
            format="json",
        )
        duplicate = self.client.post(
            reverse("auth-register"),
            {
                "email": self.user.email.upper(),
                "password": "Another-Strong-Password-991!",
                "display_name": "Different Name",
            },
            format="json",
        )
        self.assertEqual(weak.status_code, 400)
        self.assertEqual(duplicate.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.display_name, "Test Person")
        self.assertTrue(self.user.check_password("Original-Strong-Password-554!"))
        self.assertEqual(User.objects.count(), 1)

    def test_refresh_rotates_tokens_and_reuse_revokes_the_token_family(self):
        login = self.login()
        old_access = login.data["access_token"]
        old_refresh = login.data["refresh_token"]
        refreshed = self.client.post(
            reverse("auth-refresh"), {"refresh_token": old_refresh}, format="json"
        )
        self.assertEqual(refreshed.status_code, 200)
        new_access = refreshed.data["access_token"]
        new_refresh = refreshed.data["refresh_token"]
        self.assertNotEqual(old_access, new_access)
        self.assertNotEqual(old_refresh, new_refresh)
        self.assertEqual(
            self.client.get(reverse("me"), HTTP_AUTHORIZATION=f"Bearer {old_access}").status_code,
            401,
        )
        replay = self.client.post(
            reverse("auth-refresh"), {"refresh_token": old_refresh}, format="json"
        )
        self.assertEqual(replay.status_code, 401)
        self.assertEqual(
            self.client.get(reverse("me"), HTTP_AUTHORIZATION=f"Bearer {new_access}").status_code,
            401,
        )

    def test_logout_revokes_all_sessions_in_the_token_family(self):
        login = self.login()
        response = self.client.post(
            reverse("auth-logout"),
            {"refresh_token": login.data["refresh_token"]},
            format="json",
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            self.client.get(
                reverse("me"),
                HTTP_AUTHORIZATION=f"Bearer {login.data['access_token']}",
            ).status_code,
            401,
        )

    def test_legacy_json_pbkdf2_is_verified_then_upgraded_to_argon2(self):
        password = "Historic-Strong-Password-445!"
        salt = "0123456789abcdef0123456789abcdef"
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), 200_000
        ).hex()
        legacy = User(
            email="historic@example.com",
            email_normalized="historic@example.com",
            display_name="Historic User",
            password=f"aji_legacy_pbkdf2_sha256$200000${salt}${digest}",
            password_scheme=User.PasswordScheme.LEGACY_PBKDF2,
            status=User.Status.ACTIVE,
        )
        legacy.save()

        response = self.client.post(
            reverse("auth-login"),
            {"email": legacy.email, "password": password},
            format="json",
        )
        legacy.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(legacy.password.startswith("argon2"))
        self.assertEqual(legacy.password_scheme, User.PasswordScheme.ARGON2ID)
        self.assertTrue(legacy.check_password(password))

    def test_new_password_after_reset_can_log_in_from_desktop_api(self):
        raw_token = "Fictive-Reset-Token-For-Integration-Test-123456"
        PasswordResetToken.objects.create(
            user=self.user,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        confirmation = self.client.post(
            reverse("password-reset-confirm"),
            {
                "email": self.user.email,
                "token": raw_token,
                "new_password": "Reset-Strong-Password-552!",
            },
            format="json",
        )
        self.assertEqual(confirmation.status_code, 200)
        self.assertEqual(self.login("Reset-Strong-Password-552!").status_code, 200)
        self.assertEqual(self.login("Original-Strong-Password-554!").status_code, 401)


class LegacyImportCommandTests(TestCase):
    def setUp(self):
        cache.clear()

    def _source(self, directory, email="legacy@example.com"):
        salt = "abcdef0123456789abcdef0123456789"
        password = "Imported-Strong-Password-443!"
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), 200_000
        ).hex()
        path = Path(directory) / "utilisateurs.json"
        path.write_text(
            __import__("json").dumps(
                {email: {"nom": "Legacy User", "sel": salt, "hash": digest}}
            ),
            encoding="utf-8",
        )
        return path, password

    def test_default_is_dry_run_and_does_not_insert_accounts(self):
        with tempfile.TemporaryDirectory() as directory:
            source, _ = self._source(directory)
            output = __import__("io").StringIO()
            call_command("import_legacy_users", "--source", str(source), stdout=output)
        self.assertIn("DRY-RUN", output.getvalue())
        self.assertEqual(User.objects.count(), 0)

    def test_apply_is_additive_converts_legacy_hash_and_skips_existing_account(self):
        with tempfile.TemporaryDirectory() as directory:
            source, password = self._source(directory)
            call_command("import_legacy_users", "--source", str(source), "--apply", verbosity=0)
            imported = User.objects.get(email_normalized="legacy@example.com")
            original_password = imported.password
            call_command("import_legacy_users", "--source", str(source), "--apply", verbosity=0)

        imported.refresh_from_db()
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(imported.password, original_password)
        self.assertEqual(imported.password_scheme, User.PasswordScheme.LEGACY_PBKDF2)
        self.assertTrue(imported.check_password(password))
        self.assertTrue(Profile.objects.filter(user=imported).exists())
        self.assertTrue(UserPreferences.objects.filter(user=imported).exists())
        self.assertTrue(UserRole.objects.filter(user=imported, role__code=Role.Code.USER).exists())
