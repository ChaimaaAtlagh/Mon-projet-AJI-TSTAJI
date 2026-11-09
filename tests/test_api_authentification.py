import unittest
from unittest.mock import MagicMock, patch

from src.utils import api_authentification
from src.utils.api_authentification import AuthAPIError, AuthClient


def response(status, payload):
    item = MagicMock()
    item.status_code = status
    item.ok = 200 <= status < 300
    item.content = b"{}" if payload is not None else b""
    item.json.return_value = payload
    return item


class AuthClientTests(unittest.TestCase):
    def test_un_build_fige_sans_url_publique_ne_revient_pas_a_localhost(self):
        http = MagicMock()
        with (
            patch.object(api_authentification.sys, "frozen", True, create=True),
            patch.object(api_authentification, "_url_api_embarquee", return_value=""),
            patch.dict(
                api_authentification.os.environ,
                {"AJI_API_BASE_URL": "http://127.0.0.1:8000/api/v1"},
            ),
        ):
            client = AuthClient(http=http)
            self.assertEqual(client.base_url, "")
            with self.assertRaisesRegex(AuthAPIError, "adresse publique"):
                client.login("person@example.com", "Fictive-Password-123!")
        http.request.assert_not_called()

    def test_un_build_fige_prefere_l_url_publique_embarquee_a_localhost(self):
        with (
            patch.object(api_authentification.sys, "frozen", True, create=True),
            patch.object(
                api_authentification,
                "_url_api_embarquee",
                return_value="https://api.aji-tstaji.ma/api/v1",
            ),
            patch.dict(
                api_authentification.os.environ,
                {"AJI_API_BASE_URL": "http://localhost:8000/api/v1"},
            ),
        ):
            client = AuthClient()
        self.assertEqual(client.base_url, "https://api.aji-tstaji.ma/api/v1")

    def test_login_uses_api_and_keeps_bearer_tokens_in_memory(self):
        http = MagicMock()
        http.request.return_value = response(
            200,
            {
                "access_token": "a" * 40,
                "refresh_token": "r" * 64,
                "access_expires_in": 900,
                "user": {"email": "person@example.com", "display_name": "Person"},
            },
        )
        client = AuthClient("http://127.0.0.1:8000/api/v1", http=http)

        session = client.login("person@example.com", "Fictive-Password-123!")

        call = http.request.call_args
        self.assertEqual(call.args[1], "http://127.0.0.1:8000/api/v1/auth/login")
        self.assertEqual(call.kwargs["json"]["password"], "Fictive-Password-123!")
        self.assertEqual(session.user["email"], "person@example.com")
        self.assertEqual(session.get_access_token(), "a" * 40)

    def test_expiring_access_token_is_refreshed_before_protected_request(self):
        http = MagicMock()
        http.request.side_effect = [
            response(
                200,
                {
                    "access_token": "a" * 40,
                    "refresh_token": "r" * 64,
                    "access_expires_in": 900,
                    "user": {"email": "person@example.com"},
                },
            ),
            response(
                200,
                {
                    "access_token": "new-access-token" * 3,
                    "refresh_token": "new-refresh-token" * 3,
                    "access_expires_in": 900,
                    "user": {"email": "person@example.com"},
                },
            ),
            response(200, {"email": "person@example.com"}),
        ]
        client = AuthClient(http=http)
        session = client.login("person@example.com", "Fictive-Password-123!")

        with patch("src.utils.api_authentification.time.time", return_value=100):
            session.access_expires_at = 110
            result = client.get_me(session)

        self.assertEqual(result["email"], "person@example.com")
        self.assertEqual(http.request.call_count, 3)
        refresh_call = http.request.call_args_list[1]
        self.assertTrue(refresh_call.args[1].endswith("/auth/refresh"))

    def test_api_error_preserves_status_for_legacy_migration_decision(self):
        http = MagicMock()
        http.request.return_value = response(401, {"detail": "E-mail ou mot de passe incorrect."})
        client = AuthClient(http=http)

        with self.assertRaises(AuthAPIError) as raised:
            client.login("person@example.com", "wrong")

        self.assertEqual(raised.exception.status_code, 401)
        self.assertIn("incorrect", str(raised.exception))

    def test_password_reset_uses_existing_api_contract(self):
        http = MagicMock()
        http.request.side_effect = [response(202, {"detail": "sent"}), response(200, {"detail": "ok"})]
        client = AuthClient(http=http)

        client.request_password_reset("person@example.com")
        client.confirm_password_reset("person@example.com", "t" * 40, "New-Strong-Password-221!")

        request_call = http.request.call_args_list[0]
        confirm_call = http.request.call_args_list[1]
        self.assertTrue(request_call.args[1].endswith("/auth/password-reset"))
        self.assertTrue(confirm_call.args[1].endswith("/auth/password-reset/confirm"))
        self.assertEqual(confirm_call.kwargs["json"]["new_password"], "New-Strong-Password-221!")


if __name__ == "__main__":
    unittest.main()
