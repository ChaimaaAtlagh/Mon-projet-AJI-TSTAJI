import hashlib
import hmac
import logging
import secrets
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import (
    Document,
    PasswordResetThrottle,
    PasswordResetToken,
    User,
    UserSession,
)
from core.pagination import AdminUserPagination
from core.permissions import IsActiveUser, IsAdminRole, IsDocumentOwner
from core.password_reset import PasswordResetDeliveryError, send_password_reset_email
from core.password_reset_serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
)
from core.serializers import AdminUserSerializer, MeSerializer
from core.storage import PrivateDocumentError, open_private_document


LOGGER = logging.getLogger("core.password_reset")


def _throttle_hash(value):
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _consume_password_reset_limit(scope, value, limit, now):
    key_hash = _throttle_hash(f"password-reset:{scope}:{value}")
    with transaction.atomic():
        row, _ = PasswordResetThrottle.objects.select_for_update().get_or_create(
            key_hash=key_hash,
            defaults={"window_started_at": now, "request_count": 0},
        )
        if row.window_started_at + timedelta(hours=1) <= now:
            row.window_started_at = now
            row.request_count = 0
        row.request_count += 1
        row.save(update_fields=("window_started_at", "request_count"))
        return row.request_count <= limit


class PasswordResetRequestView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        now = timezone.now()
        remote_ip = request.META.get("REMOTE_ADDR", "unknown")[:64] or "unknown"

        ip_allowed = _consume_password_reset_limit(
            "ip", remote_ip, settings.PASSWORD_RESET_IP_LIMIT_PER_HOUR, now
        )
        email_allowed = False
        if ip_allowed:
            email_allowed = _consume_password_reset_limit(
                "email", email, settings.PASSWORD_RESET_EMAIL_LIMIT_PER_HOUR, now
            )

        if ip_allowed and email_allowed:
            with transaction.atomic():
                user = (
                    User.objects.select_for_update()
                    .filter(email_normalized=email)
                    .exclude(status=User.Status.SUSPENDED)
                    .first()
                )
                if user:
                    PasswordResetToken.objects.filter(
                        user=user, used_at__isnull=True
                    ).update(used_at=now)
                    raw_token = f"{secrets.randbelow(1_000_000):06d}"
                    reset_token = PasswordResetToken.objects.create(
                        user=user,
                        token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
                        expires_at=now + timedelta(
                            seconds=settings.PASSWORD_RESET_TOKEN_TTL_SECONDS
                        ),
                    )
                else:
                    raw_token = None
                    reset_token = None

            if user and raw_token and reset_token:
                try:
                    send_password_reset_email(
                        user.email,
                        user.display_name,
                        raw_token,
                    )
                except PasswordResetDeliveryError as exc:
                    PasswordResetToken.objects.filter(
                        pk=reset_token.pk, used_at__isnull=True
                    ).update(used_at=timezone.now())
                    LOGGER.warning("Password-reset delivery failed (%s).", exc.code)

        return Response(
            {
                "detail": (
                    "Si cette adresse correspond à un compte, "
                    "un e-mail de réinitialisation sera envoyé."
                )
            },
            status=202,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        raw_token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        now = timezone.now()
        remote_ip = request.META.get("REMOTE_ADDR", "unknown")[:64] or "unknown"
        ip_allowed = _consume_password_reset_limit(
            "confirm-ip",
            remote_ip,
            settings.PASSWORD_RESET_CONFIRM_IP_LIMIT_PER_HOUR,
            now,
        )
        email_allowed = _consume_password_reset_limit(
            "confirm-email",
            email,
            settings.PASSWORD_RESET_CONFIRM_EMAIL_LIMIT_PER_HOUR,
            now,
        )
        if not (ip_allowed and email_allowed):
            return Response(
                {"detail": "Le code de réinitialisation est invalide ou expiré."},
                status=400,
            )

        with transaction.atomic():
            user = User.objects.select_for_update().filter(email_normalized=email).first()
            reset_token = None
            if user and user.status != User.Status.SUSPENDED:
                reset_token = PasswordResetToken.objects.select_for_update().filter(
                    user=user,
                    token_hash=token_hash,
                    used_at__isnull=True,
                    expires_at__gt=now,
                ).first()

            if not user or not reset_token:
                return Response(
                    {"detail": "Le code de réinitialisation est invalide ou expiré."},
                    status=400,
                )

            try:
                validate_password(new_password, user=user)
            except DjangoValidationError:
                return Response(
                    {"detail": "Le nouveau mot de passe ne respecte pas les exigences de sécurité."},
                    status=400,
                )

            user.set_password(new_password)
            user.password_scheme = User.PasswordScheme.ARGON2ID
            if user.status == User.Status.RECOVERY_REQUIRED:
                user.status = User.Status.ACTIVE
            user.save(update_fields=("password", "password_scheme", "status", "updated_at"))

            reset_token.used_at = now
            reset_token.save(update_fields=("used_at",))
            UserSession.objects.filter(user=user, revoked_at__isnull=True).update(
                revoked_at=now
            )

        return Response({"detail": "Le mot de passe a été réinitialisé."}, status=200)


class MeView(APIView):
    permission_classes = (IsActiveUser,)

    def get(self, request):
        return Response(MeSerializer(request.user).data)


class AdminUserListView(ListAPIView):
    serializer_class = AdminUserSerializer
    permission_classes = (IsActiveUser, IsAdminRole)
    pagination_class = AdminUserPagination

    def get_queryset(self):
        queryset = User.objects.select_related("profile").prefetch_related("role_assignments__role")
        query = self.request.query_params.get("q", "").strip()
        status = self.request.query_params.get("status", "").strip()
        role = self.request.query_params.get("role", "").strip()
        if query:
            queryset = queryset.filter(email__icontains=query) | queryset.filter(
                email_normalized__icontains=query
            )
        if status:
            queryset = queryset.filter(status=status)
        if role:
            queryset = queryset.filter(role_assignments__role__code=role)
        return queryset.distinct().order_by("email_normalized", "id")


class DocumentDownloadView(APIView):
    permission_classes = (IsActiveUser,)

    def get(self, request, document_id):
        document = get_object_or_404(
            Document.objects.filter(
                owner_id=request.user.pk,
                status=Document.Status.AVAILABLE,
                deleted_at__isnull=True,
            ),
            pk=document_id,
        )
        self.check_object_permissions(request, document)
        try:
            file_handle = open_private_document(document.storage_key)
        except PrivateDocumentError as exc:
            raise Http404("Document unavailable") from exc

        safe_name = Path(document.original_name).name.replace("\r", "").replace("\n", "")
        return FileResponse(
            file_handle,
            as_attachment=True,
            filename=safe_name,
            content_type=document.content_type,
        )

