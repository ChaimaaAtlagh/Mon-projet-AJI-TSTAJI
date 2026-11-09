import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models import Q

from core.validators import (
    MAX_DOCUMENT_BYTES,
    validate_document_name,
    validate_document_size,
    validate_document_type,
)


class UserManager(BaseUserManager):
    use_in_migrations = True

    @staticmethod
    def normalize_login_email(email: str) -> str:
        return email.strip().lower()

    def create_user(self, email, password=None, **extra_fields):
        if not email or not email.strip():
            raise ValueError("An email address is required.")
        normalized = self.normalize_login_email(email)
        status = extra_fields.get("status", User.Status.ACTIVE)
        if not password and status != User.Status.RECOVERY_REQUIRED:
            raise ValueError("An active user must have a password.")
        user = self.model(
            email=email.strip(),
            email_normalized=normalized,
            **extra_fields,
        )
        if password:
            user.set_password(password)
            user.password_scheme = User.PasswordScheme.ARGON2ID
        else:
            user.set_unusable_password()
            user.password_scheme = User.PasswordScheme.UNUSABLE
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        RECOVERY_REQUIRED = "recovery_required", "Recovery required"

    class PasswordScheme(models.TextChoices):
        ARGON2ID = "argon2id", "Argon2id"
        LEGACY_PBKDF2 = "legacy_pbkdf2_sha256_v1", "Legacy PBKDF2-HMAC-SHA256"
        LEGACY_SHA256 = "legacy_sha256_v0", "Legacy SHA-256"
        UNUSABLE = "unusable", "Unusable password"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=254)
    email_normalized = models.EmailField(max_length=254, unique=True)
    display_name = models.CharField(max_length=150, blank=True)
    password = models.CharField(max_length=255, db_column="password_hash", blank=True)
    password_scheme = models.CharField(
        max_length=40,
        choices=PasswordScheme.choices,
        default=PasswordScheme.UNUSABLE,
    )
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.ACTIVE)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    registered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email_normalized"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ("email_normalized",)
        constraints = [
            models.CheckConstraint(
                condition=~Q(status="active", password_scheme="unusable"),
                name="active_user_has_usable_password_scheme",
            )
        ]

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    def __str__(self):
        return self.email_normalized

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip()
            self.email_normalized = self.email.lower()
        super().save(*args, **kwargs)


class Role(models.Model):
    class Code(models.TextChoices):
        USER = "user", "User"
        ADMIN = "admin", "Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, choices=Code.choices, unique=True)
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.code


class UserRole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="role_assignments")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="user_assignments")
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="role_assignments_made",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("user", "role"), name="uniq_user_role_assignment")
        ]


class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name="profile")
    first_name = models.CharField(max_length=120, blank=True)
    last_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=64, blank=True)
    city = models.CharField(max_length=120, blank=True)
    diploma = models.CharField(max_length=200, blank=True)
    sector = models.CharField(max_length=160, blank=True)
    institution = models.CharField(max_length=200, blank=True)
    skills = models.TextField(blank=True)
    job_search = models.TextField(blank=True)
    letter_draft = models.TextField(blank=True)
    education = models.TextField(blank=True)
    education_level = models.CharField(max_length=160, blank=True)
    linkedin_url = models.URLField(max_length=500, blank=True)
    portfolio_url = models.URLField(max_length=500, blank=True)
    legacy_cv_path = models.TextField(blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class UserPreferences(models.Model):
    class Locale(models.TextChoices):
        FR = "fr", "Français"
        EN = "en", "English"
        AR = "ar", "العربية"

    class AvatarChoice(models.TextChoices):
        NEUTRAL = "neutral", "Neutral"
        FEMALE = "female", "Female avatar"
        MALE = "male", "Male avatar"

    user = models.OneToOneField(User, primary_key=True, on_delete=models.PROTECT, related_name="preferences")
    locale = models.CharField(max_length=2, choices=Locale.choices, default=Locale.FR)
    avatar_choice = models.CharField(
        max_length=8,
        choices=AvatarChoice.choices,
        default=AvatarChoice.NEUTRAL,
    )
    updated_at = models.DateTimeField(auto_now=True)


class Candidature(models.Model):
    class Status(models.TextChoices):
        TO_SEND = "À envoyer", "À envoyer"
        SENT = "Envoyée", "Envoyée"
        FOLLOWED_UP = "Relancée", "Relancée"
        INTERVIEW = "Entretien", "Entretien"
        ACCEPTED = "Acceptée", "Acceptée"
        REJECTED = "Refusée", "Refusée"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="candidatures")
    company_name = models.CharField(max_length=240)
    company_domain = models.CharField(max_length=180, blank=True)
    company_district = models.CharField(max_length=180, blank=True)
    company_address = models.TextField(blank=True)
    company_phone = models.CharField(max_length=64, blank=True)
    company_email = models.EmailField(max_length=254, blank=True)
    company_website = models.URLField(max_length=500, blank=True)
    application_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.TO_SEND)
    notes = models.TextField(blank=True)
    motivation_letter = models.TextField(blank=True)
    confirmation_email_status = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-application_date", "id")


class UserSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    access_token_hash = models.CharField(max_length=64, unique=True)
    access_expires_at = models.DateTimeField()
    refresh_token_hash = models.CharField(max_length=64, unique=True)
    refresh_expires_at = models.DateTimeField()
    token_family_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    device_label = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)


class PasswordResetToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_tokens")
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)


class PasswordResetThrottle(models.Model):
    """A rolling counter keyed by a server-side HMAC, never by raw PII."""

    key_hash = models.CharField(max_length=64, primary_key=True)
    window_started_at = models.DateTimeField()
    request_count = models.PositiveIntegerField(default=0)


class Document(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        MISSING_SOURCE = "missing_source", "Missing source"
        DELETED = "deleted", "Deleted"

    class Kind(models.TextChoices):
        SOURCE_CV = "source_cv", "Source CV"
        GENERATED_CV_PDF = "generated_cv_pdf", "Generated CV PDF"
        OTHER = "other", "Other document"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name="documents")
    kind = models.CharField(max_length=24, choices=Kind.choices)
    original_name = models.CharField(max_length=255, validators=[validate_document_name])
    content_type = models.CharField(max_length=120, validators=[validate_document_type])
    size_bytes = models.PositiveBigIntegerField(validators=[validate_document_size])
    sha256 = models.CharField(max_length=64)
    storage_key = models.CharField(max_length=512, unique=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.AVAILABLE)
    source_installation_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(size_bytes__lte=MAX_DOCUMENT_BYTES),
                name="document_size_at_most_10_mib",
            )
        ]


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=100)
    target_id = models.UUIDField(null=True, blank=True)
    safe_context = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class LegacyImportBatch(models.Model):
    class Status(models.TextChoices):
        PREPARED = "prepared", "Prepared"
        IMPORTED = "imported", "Imported"
        NEEDS_RESOLUTION = "needs_resolution", "Needs resolution"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_installation_id = models.UUIDField(db_index=True)
    source_checksum = models.CharField(max_length=64)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PREPARED)
    report = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)


class LegacyRecordMap(models.Model):
    class EntityType(models.TextChoices):
        ACCOUNT = "account", "Account"
        PROFILE = "profile", "Profile"
        CANDIDATURE = "candidature", "Candidature"
        DOCUMENT = "document", "Document"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(LegacyImportBatch, on_delete=models.PROTECT, related_name="records")
    source_installation_id = models.UUIDField(db_index=True)
    entity_type = models.CharField(max_length=20, choices=EntityType.choices)
    source_table = models.CharField(max_length=100)
    source_local_key = models.CharField(max_length=255)
    source_row_checksum = models.CharField(max_length=64)
    outcome = models.CharField(max_length=24)
    conflict_code = models.CharField(max_length=80, blank=True)
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    target_profile = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True)
    target_candidature = models.ForeignKey(Candidature, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=(
                    "source_installation_id",
                    "entity_type",
                    "source_table",
                    "source_local_key",
                    "source_row_checksum",
                ),
                name="uniq_legacy_source_record_version",
            )
        ]


class LegacyProfileVersion(models.Model):
    class ResolutionStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SELECTED = "selected", "Selected"
        NOT_SELECTED = "not_selected", "Not selected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(LegacyImportBatch, on_delete=models.PROTECT, related_name="profile_versions")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="legacy_profile_versions")
    source_installation_id = models.UUIDField(db_index=True)
    payload_ciphertext = models.TextField()
    payload_checksum = models.CharField(max_length=64)
    resolution_status = models.CharField(
        max_length=20,
        choices=ResolutionStatus.choices,
        default=ResolutionStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)


class LegacyUnassignedRecord(models.Model):
    class ResolutionStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        ASSIGNED = "assigned", "Assigned"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(LegacyImportBatch, on_delete=models.PROTECT, related_name="unassigned_records")
    source_installation_id = models.UUIDField(db_index=True)
    entity_type = models.CharField(max_length=24)
    source_table = models.CharField(max_length=100)
    source_local_key = models.CharField(max_length=255)
    payload_ciphertext = models.TextField()
    payload_checksum = models.CharField(max_length=64)
    resolution_status = models.CharField(
        max_length=20,
        choices=ResolutionStatus.choices,
        default=ResolutionStatus.PENDING,
    )
    resolved_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_legacy_records",
    )
    resolution_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

