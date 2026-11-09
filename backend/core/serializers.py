from rest_framework import serializers

from core.models import User


class MeSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "display_name", "status", "roles")

    def get_roles(self, obj):
        return list(obj.role_assignments.order_by("role__code").values_list("role__code", flat=True))


class AdminUserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "city",
            "registered_at",
            "status",
            "roles",
        )

    @staticmethod
    def get_profile_value(obj, field):
        profile = getattr(obj, "profile", None)
        return getattr(profile, field, "") if profile else ""

    def get_first_name(self, obj):
        return self.get_profile_value(obj, "first_name")

    def get_last_name(self, obj):
        return self.get_profile_value(obj, "last_name")

    def get_city(self, obj):
        return self.get_profile_value(obj, "city")

    def get_roles(self, obj):
        return list(obj.role_assignments.order_by("role__code").values_list("role__code", flat=True))

