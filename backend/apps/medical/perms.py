from rest_framework.permissions import IsAuthenticated

from apps.users.models import EmployeeRole


class IsNurse(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.employee_role == EmployeeRole.NURSE