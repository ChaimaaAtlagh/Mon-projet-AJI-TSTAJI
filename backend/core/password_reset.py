"""Secure password-reset tokens and Brevo transactional email delivery."""

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


LOGGER = logging.getLogger("core.password_reset")
BREVO_SEND_EMAIL_URL = "https://api.brevo.com/v3/smtp/email"


class PasswordResetDeliveryError(Exception):
    """A sanitized failure code; never includes request headers or response data."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def send_password_reset_email(recipient_email, recipient_name, token):
    api_key = settings.BREVO_API_KEY
    sender_email = settings.BREVO_SENDER_EMAIL
    if not api_key:
        raise PasswordResetDeliveryError("missing_api_key")
    if not sender_email:
        raise PasswordResetDeliveryError("missing_sender")

    greeting = f"Bonjour {recipient_name}," if recipient_name else "Bonjour,"
    text_content = (
        f"{greeting}\n\n"
        "Voici votre code de réinitialisation du mot de passe AJI TSTAJI :\n"
        f"{token}\n\n"
        "Ce code est valable 30 minutes et ne peut être utilisé qu'une seule fois.\n"
        "Si vous n'avez pas demandé cette réinitialisation, ignorez cet e-mail."
    )
    payload = {
        "sender": {"name": settings.BREVO_SENDER_NAME, "email": sender_email},
        "to": [{"email": recipient_email}],
        "subject": "Réinitialisation de votre mot de passe AJI TSTAJI",
        "textContent": text_content,
    }
    request = Request(
        BREVO_SEND_EMAIL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            if response.status not in (200, 201, 202):
                raise PasswordResetDeliveryError("unexpected_http_status")
    except HTTPError as exc:
        LOGGER.warning("Brevo password-reset request failed (HTTP %s).", exc.code)
        raise PasswordResetDeliveryError(f"http_{exc.code}") from None
    except (URLError, TimeoutError, OSError):
        LOGGER.warning("Brevo password-reset request failed (network error).")
        raise PasswordResetDeliveryError("network_error") from None
