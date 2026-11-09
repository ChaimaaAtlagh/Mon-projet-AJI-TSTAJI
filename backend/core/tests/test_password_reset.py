import hashlib
import json
import re
import secrets
from datetime import timedelta
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import PasswordResetToken, User, UserSession


class PasswordResetApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            "person@example.com", "Initial-Strong-Password-876!", display_name="Person"
        )
        self.request_url = reverse("password-reset-request")
        self.confirm_url = reverse("password-reset-confirm")

    def request_reset(self, email=None):
        return self.client.post(
            self.request_url,
            {"email": email or self.user.email},
            format="json",
            REMOTE_ADDR="192.0.2.10",
        )

    @patch("core.views.send_password_reset_email")
    def test_request_response_does_not_reveal_whether_account_exists(self, send_email):
        known = self.request_reset(self.user.email)
        unknown = self.request_reset("missing@example.com")

        self.assertEqual(known.status_code, 202)
        self.assertEqual(unknown.status_code, 202)
        self.assertEqual(known.data, unknown.data)
        self.assertNotIn(self.user.email, str(known.data))
        self.assertEqual(send_email.call_count, 1)

    @patch("core.views.send_password_reset_email")
    def test_request_saves_only_hash_with_thirty_minute_expiry(self, send_email):
        self.request_reset()

        raw_token = send_email.call_args.args[2]
        self.assertRegex(raw_token, re.compile(r"^\d{6}$"))
        saved = PasswordResetToken.objects.get(user=self.user)
        self.assertEqual(saved.token_hash, hashlib.sha256(raw_token.encode()).hexdigest())
        self.assertNotEqual(saved.token_hash, raw_token)
        self.assertAlmostEqual(
            (saved.expires_at - saved.created_at).total_seconds(),
            30 * 60,
            delta=1,
        )

    @patch("core.views.send_password_reset_email")
    def test_request_is_rate_limited_per_email_without_changing_response(self, send_email):
        with override_settings(PASSWORD_RESET_EMAIL_LIMIT_PER_HOUR=2):
            responses = [self.request_reset() for _ in range(3)]

        self.assertTrue(all(response.status_code == 202 for response in responses))
        self.assertEqual(responses[0].data, responses[2].data)
        self.assertEqual(send_email.call_count, 2)

    @patch("core.views.send_password_reset_email")
    def test_request_is_rate_limited_per_ip(self, send_email):
        second_user = User.objects.create_user(
            "second@example.com", "Another-Strong-Password-875!"
        )
        with override_settings(PASSWORD_RESET_IP_LIMIT_PER_HOUR=1):
            first = self.request_reset(self.user.email)
            second = self.request_reset(second_user.email)

        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(first.data, second.data)
        self.assertEqual(send_email.call_count, 1)

    @patch("core.views.send_password_reset_email")
    def test_failed_delivery_invalidates_token_and_keeps_generic_response(self, send_email):
        from core.password_reset import PasswordResetDeliveryError

        send_email.side_effect = PasswordResetDeliveryError("network_error")
        with self.assertLogs("core.password_reset", level="WARNING") as captured:
            response = self.request_reset()

        saved = PasswordResetToken.objects.get(user=self.user)
        self.assertEqual(response.status_code, 202)
        self.assertIsNotNone(saved.used_at)
        self.assertNotIn(self.user.email, " ".join(captured.output))

    @patch("core.views.send_password_reset_email")
    def test_suspended_accounts_do_not_receive_reset_email(self, send_email):
        self.user.status = User.Status.SUSPENDED
        self.user.save(update_fields=("status",))

        response = self.request_reset()

        self.assertEqual(response.status_code, 202)
        send_email.assert_not_called()
        self.assertFalse(PasswordResetToken.objects.filter(user=self.user).exists())

    def create_token(self, *, expires_at=None):
        raw_token = secrets.token_urlsafe(32)
        row = PasswordResetToken.objects.create(
            user=self.user,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            expires_at=expires_at or timezone.now() + timedelta(minutes=30),
        )
        return raw_token, row

    def confirm(self, token, password="A-New-Strong-Password-998!"):
        return self.client.post(
            self.confirm_url,
            {"email": self.user.email, "token": token, "new_password": password},
            format="json",
        )

    def test_confirm_changes_password_consumes_token_and_revokes_sessions(self):
        raw_token, reset_token = self.create_token()
        session = UserSession.objects.create(
            user=self.user,
            access_token_hash="a" * 64,
            access_expires_at=timezone.now() + timedelta(minutes=5),
            refresh_token_hash="b" * 64,
            refresh_expires_at=timezone.now() + timedelta(days=1),
        )

        response = self.confirm(raw_token)

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        reset_token.refresh_from_db()
        session.refresh_from_db()
        self.assertTrue(self.user.check_password("A-New-Strong-Password-998!"))
        self.assertEqual(self.user.password_scheme, User.PasswordScheme.ARGON2ID)
        self.assertIsNotNone(reset_token.used_at)
        self.assertIsNotNone(session.revoked_at)

    def test_confirm_rejects_used_and_expired_tokens(self):
        raw_token, reset_token = self.create_token()
        first = self.confirm(raw_token)
        second = self.confirm(raw_token)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)

        expired_token, _ = self.create_token(expires_at=timezone.now() - timedelta(seconds=1))
        expired = self.confirm(expired_token)
        self.assertEqual(expired.status_code, 400)

    def test_confirm_rate_limits_code_guesses_per_email_and_ip(self):
        with override_settings(
            PASSWORD_RESET_CONFIRM_EMAIL_LIMIT_PER_HOUR=2,
            PASSWORD_RESET_CONFIRM_IP_LIMIT_PER_HOUR=2,
        ):
            responses = [self.confirm("000000") for _ in range(3)]

        self.assertEqual([response.status_code for response in responses], [400, 400, 400])
        self.assertEqual(responses[0].data, responses[2].data)

    def test_confirm_accepts_unexpired_legacy_long_token(self):
        # Requests sent immediately before rollout still complete successfully.
        raw_token, _ = self.create_token()
        response = self.confirm(raw_token)
        self.assertEqual(response.status_code, 200)


class BrevoPasswordResetDeliveryTests(TestCase):
    @override_settings(
        BREVO_API_KEY="fictive-brevo-test-key",
        BREVO_SENDER_EMAIL="sender@example.com",
        BREVO_SENDER_NAME="AJI TSTAJI",
    )
    @patch("core.password_reset.urlopen")
    def test_transactional_email_uses_brevo_send_endpoint_and_api_key_header(
        self, urlopen_mock
    ):
        from core.password_reset import send_password_reset_email

        response = MagicMock()
        response.status = 201
        response.__enter__.return_value = response
        urlopen_mock.return_value = response

        send_password_reset_email("person@example.com", "Person", "secure-test-token")

        request = urlopen_mock.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.brevo.com/v3/smtp/email")
        self.assertEqual(request.get_header("Api-key"), "fictive-brevo-test-key")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["sender"]["email"], "sender@example.com")
        self.assertEqual(payload["to"], [{"email": "person@example.com"}])
        self.assertIn("secure-test-token", payload["textContent"])

    @override_settings(BREVO_API_KEY="fictive-brevo-test-key", BREVO_SENDER_EMAIL="sender@example.com")
    @patch("core.password_reset.urlopen")
    def test_brevo_failure_does_not_log_or_raise_api_key(self, urlopen_mock):
        from core.password_reset import PasswordResetDeliveryError, send_password_reset_email

        urlopen_mock.side_effect = HTTPError(
            "https://api.brevo.com/v3/smtp/email", 401, "Unauthorized", {}, None
        )

        with self.assertLogs("core.password_reset", level="WARNING") as captured:
            with self.assertRaises(PasswordResetDeliveryError) as raised:
                send_password_reset_email("person@example.com", "Person", "token")

        self.assertNotIn("fictive-brevo-test-key", str(raised.exception))
        self.assertNotIn("fictive-brevo-test-key", " ".join(captured.output))

    @override_settings(BREVO_API_KEY="", BREVO_SENDER_EMAIL="sender@example.com")
    @patch("core.password_reset.urlopen")
    def test_missing_api_key_fails_without_network_request(self, urlopen_mock):
        from core.password_reset import PasswordResetDeliveryError, send_password_reset_email

        with self.assertRaises(PasswordResetDeliveryError) as raised:
            send_password_reset_email("person@example.com", "Person", "token")

        self.assertEqual(raised.exception.code, "missing_api_key")
        urlopen_mock.assert_not_called()
