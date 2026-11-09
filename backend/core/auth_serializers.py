"""Input validation for the public authentication endpoints."""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from core.models import User


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    device_label = serializers.CharField(max_length=160, required=False, allow_blank=True)

    def validate_email(self, value):
        return value.strip().lower()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(min_length=8, max_length=128, trim_whitespace=False, write_only=True)
    display_name = serializers.CharField(max_length=150)
    first_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=64, required=False, allow_blank=True)
    city = serializers.CharField(max_length=120, required=False, allow_blank=True)
    diploma = serializers.CharField(max_length=200, required=False, allow_blank=True)
    sector = serializers.CharField(max_length=160, required=False, allow_blank=True)
    institution = serializers.CharField(max_length=200, required=False, allow_blank=True)
    skills = serializers.CharField(required=False, allow_blank=True)
    job_search = serializers.CharField(required=False, allow_blank=True)
    device_label = serializers.CharField(max_length=160, required=False, allow_blank=True)

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email_normalized=normalized).exists():
            raise serializers.ValidationError("Un compte existe déjà avec cette adresse e-mail.")
        return normalized

    def validate(self, attrs):
        candidate = User(email=attrs["email"], display_name=attrs["display_name"].strip())
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        attrs["display_name"] = attrs["display_name"].strip()
        if not attrs.get("first_name"):
            name_parts = attrs["display_name"].split(maxsplit=1)
            attrs["first_name"] = name_parts[0] if name_parts else ""
            if not attrs.get("last_name") and len(name_parts) > 1:
                attrs["last_name"] = name_parts[1]
        for field in ("first_name", "last_name", "phone", "city", "diploma", "sector", "institution", "skills", "job_search", "device_label"):
            attrs.setdefault(field, "")
        return attrs


class RefreshSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(min_length=32, max_length=128, trim_whitespace=False)


class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(min_length=32, max_length=128, trim_whitespace=False)
