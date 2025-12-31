from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticatedOrReadOnly, IsAuthenticated

from apps.users.models import UserRole, EmployeeRole


class IsDoctorOrPatientOwner(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, profile):
        if request.user.user_role == UserRole.EMPLOYEE and request.user.employee_role == EmployeeRole.DOCTOR:
            return True

        if request.method in SAFE_METHODS:
            return request.user == profile.user