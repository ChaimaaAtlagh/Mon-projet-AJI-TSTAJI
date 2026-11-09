from rest_framework.permissions import BasePermission


class IsActiveUser(BasePermission):
    message = "An active account is required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.status == request.user.Status.ACTIVE
        )


class IsAdminRole(BasePermission):
    message = "The admin role is required."

    def has_permission(self, request, view):
        if not IsActiveUser().has_permission(request, view):
            return False
        return request.user.role_assignments.filter(role__code="admin").exists()


class IsDocumentOwner(BasePermission):
    message = "Only the document owner can access its contents."

    def has_object_permission(self, request, view, obj):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(obj, "owner_id", None) == request.user.pk
        )

