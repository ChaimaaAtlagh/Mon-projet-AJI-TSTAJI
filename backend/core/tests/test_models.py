from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import (
    Candidature,
    Document,
    Profile,
    Role,
    User,
    UserPreferences,
    UserRole,
)
from core.validators import MAX_DOCUMENT_BYTES


class UserModelTests(TestCase):
    def test_custom_user_is_active_model_and_normalizes_email(self):
        user = User.objects.create_user("  Test.User@Example.com  ", "Fictive-Test-Password-123!")
        self.assertEqual(user.email_normalized, "test.user@example.com")
        self.assertEqual(user.password_scheme, User.PasswordScheme.ARGON2ID)
        self.assertTrue(user.check_password("Fictive-Test-Password-123!"))
        self.assertTrue(user.is_active)

    def test_normalized_email_is_unique(self):
        User.objects.create_user("test@example.com", "Fictive-Test-Password-123!")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user("TEST@example.com", "Fictive-Test-Password-123!")

    def test_preferences_default_to_french_and_neutral_avatar(self):
        user = User.objects.create_user("preferences@example.com", "Fictive-Test-Password-123!")
        preferences = UserPreferences.objects.create(user=user)
        self.assertEqual(preferences.locale, UserPreferences.Locale.FR)
        self.assertEqual(preferences.avatar_choice, UserPreferences.AvatarChoice.NEUTRAL)

    def test_profile_is_one_to_one(self):
        user = User.objects.create_user("profile@example.com", "Fictive-Test-Password-123!")
        Profile.objects.create(user=user)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Profile.objects.create(user=user)

    def test_role_assignment_is_unique(self):
        user = User.objects.create_user("role@example.com", "Fictive-Test-Password-123!")
        role = Role.objects.create(code=Role.Code.USER, name="User")
        UserRole.objects.create(user=user, role=role)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserRole.objects.create(user=user, role=role)


class CandidatureAndDocumentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("records@example.com", "Fictive-Test-Password-123!")

    def test_candidature_status_defaults_to_to_send(self):
        candidature = Candidature.objects.create(user=self.user, company_name="Fake Company")
        self.assertEqual(candidature.status, Candidature.Status.TO_SEND)

    def test_document_accepts_fake_pdf_metadata_within_size_limit(self):
        document = Document(
            owner=self.user,
            kind=Document.Kind.SOURCE_CV,
            original_name="fake-cv.pdf",
            content_type="application/pdf",
            size_bytes=MAX_DOCUMENT_BYTES,
            sha256="a" * 64,
            storage_key="documents/fake-cv.pdf",
        )
        document.full_clean()

    def test_document_rejects_over_limit_size(self):
        document = Document(
            owner=self.user,
            kind=Document.Kind.SOURCE_CV,
            original_name="fake-cv.pdf",
            content_type="application/pdf",
            size_bytes=MAX_DOCUMENT_BYTES + 1,
            sha256="a" * 64,
            storage_key="documents/too-large.pdf",
        )
        with self.assertRaises(ValidationError):
            document.full_clean()

    def test_document_rejects_unapproved_extension(self):
        document = Document(
            owner=self.user,
            kind=Document.Kind.SOURCE_CV,
            original_name="fake-cv.exe",
            content_type="application/pdf",
            size_bytes=10,
            sha256="a" * 64,
            storage_key="documents/fake-cv.exe",
        )
        with self.assertRaises(ValidationError):
            document.full_clean()

