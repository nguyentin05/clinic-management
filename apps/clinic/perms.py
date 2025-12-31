from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticatedOrReadOnly, IsAuthenticated

from apps.users.models import UserRole, EmployeeRole


class IsOwnerAppointment(IsAuthenticated):
    def has_object_permission(self, request, view, appointment):
        return super().has_permission(request, view) and (request.user == appointment.patient or request.user == appointment.doctor)

class IsPatient(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.user_role == UserRole.PATIENT