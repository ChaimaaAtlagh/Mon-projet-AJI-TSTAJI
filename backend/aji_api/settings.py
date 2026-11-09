"""Local-only settings; secrets are loaded from backend/.env or the process env."""

import os
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ImproperlyConfigured(f"Required environment variable is missing: {name}")
    return value


def _database_config() -> dict:
    """Accept a hosted PostgreSQL URL while preserving local DB_* settings."""
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url:
        parsed = urlsplit(database_url)
        if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
            raise ImproperlyConfigured("DATABASE_URL must be a PostgreSQL URL.")
        try:
            port = parsed.port or 5432
        except ValueError as exc:
            raise ImproperlyConfigured("DATABASE_URL has an invalid port.") from exc
        name = unquote(parsed.path.lstrip("/"))
        if not name or not parsed.username or parsed.password is None:
            raise ImproperlyConfigured("DATABASE_URL is missing a database name or credentials.")
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": name,
            "USER": unquote(parsed.username),
            "PASSWORD": unquote(parsed.password),
            "HOST": parsed.hostname,
            "PORT": str(port),
            "CONN_MAX_AGE": 0,
            "OPTIONS": {"sslmode": query.get("sslmode", "require")},
        }

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": required_env("DB_NAME"),
        "USER": required_env("DB_USER"),
        "PASSWORD": required_env("DB_PASSWORD"),
        "HOST": required_env("DB_HOST"),
        "PORT": required_env("DB_PORT"),
        "CONN_MAX_AGE": 0,
    }


SECRET_KEY = required_env("DJANGO_SECRET_KEY")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").strip().lower() in {"1", "true", "yes"}
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if host.strip()
]
render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if render_hostname and render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_hostname)

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

DATABASES = {"default": _database_config()}

# Must be set before the first migration is generated.
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
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.authentication.SessionBearerAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
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

PRIVATE_DOCUMENT_ROOT = Path(
    os.environ.get("PRIVATE_DOCUMENT_ROOT", str(BASE_DIR / ".private_documents"))
).resolve()

# The only Brevo value read from the environment is the API credential.
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
BREVO_SENDER_EMAIL = os.environ.get("BREVO_SENDER_EMAIL", "").strip()
BREVO_SENDER_NAME = "AJI TSTAJI"
PASSWORD_RESET_TOKEN_TTL_SECONDS = 30 * 60
PASSWORD_RESET_EMAIL_LIMIT_PER_HOUR = 3
PASSWORD_RESET_IP_LIMIT_PER_HOUR = 15
PASSWORD_RESET_CONFIRM_EMAIL_LIMIT_PER_HOUR = 10
PASSWORD_RESET_CONFIRM_IP_LIMIT_PER_HOUR = 30

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

