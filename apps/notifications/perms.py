from rest_framework.permissions import BasePermission


class IsOwnerNotification(BasePermission):
    def has_object_permission(self, request, view, notification):
        return notification.recipient == request.user