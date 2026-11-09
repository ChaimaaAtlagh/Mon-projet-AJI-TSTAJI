"""Password login, registration and opaque bearer-session lifecycle."""

import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from core.auth_serializers import LoginSerializer, LogoutSerializer, RefreshSerializer, RegisterSerializer
from core.models import Profile, Role, User, UserPreferences, UserRole, UserSession
from core.serializers import MeSerializer


ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)
_DUMMY_PASSWORD_HASH = make_password("constant-time-authentication-probe")


def _digest(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _issue_session(user, device_label="", token_family_id=None):
    access_token = secrets.token_urlsafe(32)
    refresh_token = secrets.token_urlsafe(48)
    now = timezone.now()
    session = UserSession.objects.create(
        user=user,
        access_token_hash=_digest(access_token),
        access_expires_at=now + ACCESS_TOKEN_TTL,
        refresh_token_hash=_digest(refresh_token),
        refresh_expires_at=now + REFRESH_TOKEN_TTL,
        device_label=device_label[:160],
        **({"token_family_id": token_family_id} if token_family_id else {}),
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "access_expires_in": int(ACCESS_TOKEN_TTL.total_seconds()),
        "refresh_expires_in": int(REFRESH_TOKEN_TTL.total_seconds()),
        "user": MeSerializer(user).data,
        "session_id": str(session.pk),
    }


def _invalid_credentials():
    return Response({"detail": "E-mail ou mot de passe incorrect."}, status=401)


class LoginView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "auth"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        user = User.objects.filter(email_normalized=email).first()
        password_matches = (
            user.check_password(password)
            if user is not None
            else check_password(password, _DUMMY_PASSWORD_HASH)
        )
        if not password_matches or user is None or user.status != User.Status.ACTIVE:
            return _invalid_credentials()

        now = timezone.now()
        update_fields = ["last_login"]
        user.last_login = now
        # check_password upgrades hashes marked must_update; keep the scheme
        # metadata aligned with the Argon2 hash saved by Django's setter.
        if user.password_scheme != User.PasswordScheme.ARGON2ID:
            user.password_scheme = User.PasswordScheme.ARGON2ID
            update_fields.append("password_scheme")
        user.save(update_fields=update_fields)
        return Response(_issue_session(user, serializer.validated_data.get("device_label", "")))


class RegisterView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "auth"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        with transaction.atomic():
            user = User.objects.create_user(
                values["email"],
                values["password"],
                display_name=values["display_name"],
                registered_at=timezone.now(),
            )
            Profile.objects.create(
                user=user,
                first_name=values["first_name"],
                last_name=values["last_name"],
                phone=values["phone"],
                city=values["city"],
                diploma=values["diploma"],
                sector=values["sector"],
                institution=values["institution"],
                skills=values["skills"],
                job_search=values["job_search"],
            )
            UserPreferences.objects.get_or_create(user=user)
            role, _ = Role.objects.get_or_create(
                code=Role.Code.USER,
                defaults={"name": "Utilisateur"},
            )
            UserRole.objects.get_or_create(user=user, role=role)
            payload = _issue_session(user, values.get("device_label", ""))
        return Response(payload, status=201)


class RefreshView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "auth_refresh"

    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token_hash = _digest(serializer.validated_data["refresh_token"])
        now = timezone.now()

        with transaction.atomic():
            old_session = (
                UserSession.objects.select_for_update()
                .select_related("user")
                .filter(refresh_token_hash=token_hash)
                .first()
            )
            if old_session is None:
                return Response({"detail": "Session invalide ou expirée."}, status=401)
            if old_session.revoked_at is not None:
                # Reuse of a rotated token invalidates all sessions in its family.
                UserSession.objects.filter(
                    token_family_id=old_session.token_family_id,
                    revoked_at__isnull=True,
                ).update(revoked_at=now)
                return Response({"detail": "Session invalide ou expirée."}, status=401)
            if old_session.refresh_expires_at <= now or not old_session.user.is_active:
                old_session.revoked_at = now
                old_session.save(update_fields=("revoked_at",))
                return Response({"detail": "Session invalide ou expirée."}, status=401)

            old_session.revoked_at = now
            old_session.save(update_fields=("revoked_at",))
            payload = _issue_session(
                old_session.user,
                old_session.device_label,
                old_session.token_family_id,
            )
        return Response(payload)


class LogoutView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if serializer.is_valid():
            token_hash = _digest(serializer.validated_data["refresh_token"])
            now = timezone.now()
            session = UserSession.objects.filter(refresh_token_hash=token_hash).first()
            if session is not None:
                UserSession.objects.filter(
                    token_family_id=session.token_family_id,
                    revoked_at__isnull=True,
                ).update(revoked_at=now)
        # Idempotent response: do not reveal whether a token was recognized.
        return Response(status=204)
