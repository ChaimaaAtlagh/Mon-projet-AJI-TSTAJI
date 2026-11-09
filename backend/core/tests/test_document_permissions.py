from pathlib import Path
import hashlib
import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from core.models import Document, Role, User, UserRole


class DocumentAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user("owner@example.com", "Fictive-Test-Password-123!")
        self.other_user = User.objects.create_user("other@example.com", "Fictive-Test-Password-123!")
        self.admin = User.objects.create_user("admin@example.com", "Fictive-Test-Password-123!")
        admin_role = Role.objects.create(code=Role.Code.ADMIN, name="Admin")
        UserRole.objects.create(user=self.admin, role=admin_role)

        self.temp_dir = tempfile.TemporaryDirectory(
            dir=Path(__file__).resolve().parents[2],
            prefix=".test_private_documents_",
        )
        self.addCleanup(self.temp_dir.cleanup)
        self.settings_override = override_settings(PRIVATE_DOCUMENT_ROOT=self.temp_dir.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

        self.fake_pdf_bytes = b"%PDF-1.4 fictional test document"
        self.storage_key = "owner/fake-cv.pdf"
        file_path = Path(self.temp_dir.name) / self.storage_key
        file_path.parent.mkdir(parents=True)
        file_path.write_bytes(self.fake_pdf_bytes)
        self.document = Document.objects.create(
            owner=self.owner,
            kind=Document.Kind.SOURCE_CV,
            original_name="fake-cv.pdf",
            content_type="application/pdf",
            size_bytes=len(self.fake_pdf_bytes),
            sha256=hashlib.sha256(self.fake_pdf_bytes).hexdigest(),
            storage_key=self.storage_key,
        )

    def download(self):
        return self.client.get(
            reverse("document-download", kwargs={"document_id": self.document.id})
        )

    def test_owner_can_download_own_document(self):
        self.client.force_authenticate(user=self.owner)
        response = self.download()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), self.fake_pdf_bytes)

    def test_other_user_cannot_access_document_content(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.download()
        self.assertEqual(response.status_code, 404)

    def test_admin_role_does_not_grant_access_to_another_users_cv_content(self):
        self.client.force_authenticate(user=self.admin)
        response = self.download()
        self.assertEqual(response.status_code, 404)

    def test_document_response_does_not_expose_storage_key(self):
        self.client.force_authenticate(user=self.owner)
        response = self.download()
        try:
            self.assertNotIn("storage_key", response.headers)
            self.assertNotIn("owner@example.com", response.headers.get("Content-Disposition", ""))
        finally:
            response.close()

