import hashlib

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from core.models import UserSession


class SessionBearerAuthentication(BaseAuthentication):
    """Authenticate an opaque bearer token by its server-side SHA-256 digest."""

    keyword = "Bearer"

    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header:
            return None

        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != self.keyword.lower():
            raise AuthenticationFailed("Invalid authorization header.")

        token_digest = hashlib.sha256(parts[1].encode("utf-8")).hexdigest()
        session = (
            UserSession.objects.select_related("user")
            .filter(access_token_hash=token_digest, revoked_at__isnull=True)
            .first()
        )
        if not session or session.access_expires_at <= timezone.now():
            raise AuthenticationFailed("Invalid or expired session.")
        if not session.user.is_active:
            raise AuthenticationFailed("Account is inactive.")

        return session.user, session

    def authenticate_header(self, request):
        return self.keyword

