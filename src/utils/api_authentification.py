"""Client HTTP for the Django authentication API used by the Desktop app."""

import json
import os
import sys
import time
import ipaddress
from urllib.parse import urlsplit

import requests
from dotenv import load_dotenv
from src.utils.paths import chemin_configuration, chemin_ressource


load_dotenv(chemin_configuration(), override=False)


def _url_api_publique(valeur):
    """Return only a usable HTTPS API URL; packaged builds never use localhost."""
    if not valeur:
        return ""
    valeur = valeur.strip().rstrip("/")
    try:
        parsed = urlsplit(valeur)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not host or parsed.username or parsed.password:
            return ""
        if host in {"localhost", "localhost.localdomain"} or host.endswith(
            (".localhost", ".local", ".example", ".test", ".invalid")
        ):
            return ""
        if host in {"example.com", "example.org", "example.net"} or host.endswith(
            (".example.com", ".example.org", ".example.net")
        ):
            return ""
        if host.startswith("127.") or host in {"0.0.0.0", "::1"}:
            return ""
        if not parsed.path.rstrip("/").lower().endswith("/api/v1"):
            return ""
        if parsed.query or parsed.fragment:
            return ""
        try:
            if not ipaddress.ip_address(host).is_global:
                return ""
        except ValueError:
            pass
        return valeur
    except ValueError:
        return ""


def _url_api_embarquee():
    """Read the non-secret, build-time API URL bundled with a Windows release."""
    if not getattr(sys, "frozen", False):
        return ""
    chemin = chemin_ressource("config", "client_api.json")
    try:
        configuration = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return _url_api_publique(configuration.get("api_base_url", ""))


def _url_api_par_defaut(base_url=None):
    if not getattr(sys, "frozen", False):
        return (
            base_url
            or os.environ.get("AJI_API_BASE_URL")
            or "http://127.0.0.1:8000/api/v1"
        ).rstrip("/")

    # In a packaged app, a public build URL wins over an unsafe local override.
    for candidate in (base_url or os.environ.get("AJI_API_BASE_URL"), _url_api_embarquee()):
        public_url = _url_api_publique(candidate)
        if public_url:
            return public_url
    return ""


class AuthAPIError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class AuthClient:
    def __init__(self, base_url=None, timeout=8, http=None):
        self.base_url = _url_api_par_defaut(base_url)
        self.timeout = timeout
        self.http = http or requests.Session()

    @staticmethod
    def _message(payload, fallback):
        if not isinstance(payload, dict):
            return fallback
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
        for value in payload.values():
            if isinstance(value, list) and value and isinstance(value[0], str):
                return value[0]
            if isinstance(value, dict):
                nested = AuthClient._message(value, "")
                if nested:
                    return nested
        return fallback

    def _request(self, method, endpoint, *, data=None, access_token=None):
        if not self.base_url:
            raise AuthAPIError(
                "L’adresse publique de l’API AJI TSTAJI n’est pas configurée "
                "pour cette version. Réinstallez une version à jour."
            )
        headers = {}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        try:
            response = self.http.request(
                method,
                f"{self.base_url}/{endpoint.lstrip('/')}",
                json=data,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise AuthAPIError(
                "Impossible de joindre le backend AJI TSTAJI. Vérifiez qu'il est démarré."
            ) from exc

        try:
            payload = response.json() if response.content else {}
        except (ValueError, requests.JSONDecodeError):
            payload = {}
        if not response.ok:
            fallback = f"La demande a échoué (HTTP {response.status_code})."
            raise AuthAPIError(self._message(payload, fallback), response.status_code)
        return payload

    def login(self, email, password, device_label="AJI TSTAJI Desktop"):
        payload = self._request(
            "POST",
            "auth/login",
            data={"email": email, "password": password, "device_label": device_label},
        )
        return DesktopAuthSession(self, payload)

    def register(self, email, password, *, device_label="AJI TSTAJI Desktop", **profile):
        payload = self._request(
            "POST",
            "auth/register",
            data={
                "email": email,
                "password": password,
                "device_label": device_label,
                **profile,
            },
        )
        return DesktopAuthSession(self, payload)

    def request_password_reset(self, email):
        return self._request("POST", "auth/password-reset", data={"email": email})

    def confirm_password_reset(self, email, token, new_password):
        return self._request(
            "POST",
            "auth/password-reset/confirm",
            data={"email": email, "token": token, "new_password": new_password},
        )

    def refresh_session(self, refresh_token):
        return self._request(
            "POST", "auth/refresh", data={"refresh_token": refresh_token}
        )

    def get_me(self, session):
        token = session.get_access_token()
        return self._request("GET", "me", access_token=token)

    def assistant_chat(self, session, messages):
        token = session.get_access_token()
        return self._request(
            "POST",
            "assistant/chat",
            data={"messages": messages},
            access_token=token,
        )


class DesktopAuthSession:
    """Opaque tokens kept in memory and refreshed before protected requests."""

    def __init__(self, client, payload):
        self.client = client
        self.user = payload.get("user", {})
        self._set_tokens(payload)

    def _set_tokens(self, payload):
        self.access_token = payload["access_token"]
        self.refresh_token = payload["refresh_token"]
        self.access_expires_at = time.time() + int(payload.get("access_expires_in", 900))

    def get_access_token(self):
        if not self.access_token:
            raise AuthAPIError("La session est terminée.", 401)
        if self.access_expires_at <= time.time() + 30:
            try:
                payload = self.client.refresh_session(self.refresh_token)
            except AuthAPIError as exc:
                if exc.status_code == 401:
                    self.access_token = ""
                    self.refresh_token = ""
                raise
            self._set_tokens(payload)
            self.user = payload.get("user", self.user)
        return self.access_token

    def logout(self):
        if not self.refresh_token:
            return
        token = self.refresh_token
        try:
            self.client._request("POST", "auth/logout", data={"refresh_token": token})
        finally:
            self.access_token = ""
            self.refresh_token = ""

    def assistant_chat(self, messages):
        """Call the authenticated assistant relay without exposing its key."""
        return self.client.assistant_chat(self, messages)
