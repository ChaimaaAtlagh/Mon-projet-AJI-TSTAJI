"""Isolated settings for automated tests; never connects to PostgreSQL."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "test-only-not-a-deployment-secret"
DEBUG = True
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "core.apps.CoreConfig",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]
ROOT_URLCONF = "aji_api.urls"
TEMPLATES = []
WSGI_APPLICATION = "aji_api.wsgi.application"
ASGI_APPLICATION = "aji_api.asgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
AUTH_USER_MODEL = "core.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "core.hashers.LegacyDesktopPBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["core.authentication.SessionBearerAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_THROTTLE_RATES": {
        "auth": "10/minute",
        "auth_refresh": "30/minute",
        "assistant": "30/hour",
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
PRIVATE_DOCUMENT_ROOT = ".test-private-documents"
BREVO_API_KEY = ""
BREVO_SENDER_EMAIL = "test@example.invalid"
BREVO_SENDER_NAME = "AJI tests"
PASSWORD_RESET_TOKEN_TTL_SECONDS = 30 * 60
PASSWORD_RESET_EMAIL_LIMIT_PER_HOUR = 3
PASSWORD_RESET_IP_LIMIT_PER_HOUR = 15
PASSWORD_RESET_CONFIRM_EMAIL_LIMIT_PER_HOUR = 10
PASSWORD_RESET_CONFIRM_IP_LIMIT_PER_HOUR = 30
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
