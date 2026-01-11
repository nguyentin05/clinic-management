from rest_framework.permissions import BasePermission, IsAuthenticated

from apps.users.models import UserRole, EmployeeRole

class IsEmployee(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.user_role == UserRole.EMPLOYEE


class IsPatient(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.user_role == UserRole.PATIENT


class IsDoctor(IsEmployee):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.employee_role == EmployeeRole.DOCTOR


class IsNurse(IsEmployee):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.employee_role == EmployeeRole.NURSE


class IsPharmacist(IsEmployee):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.employee_role == EmployeeRole.PHARMACIST

class IsDoctorOrNurse(IsEmployee):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.employee_role in [EmployeeRole.DOCTOR,
                                                                                        EmployeeRole.NURSE]

class IsDoctorOrPharmacist(IsEmployee):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.employee_role in [EmployeeRole.DOCTOR,
                                                                                        EmployeeRole.PHARMACIST]

class IsDoctorOrPatient(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and \
            (request.user.user_role == UserRole.PATIENT or
            (request.user.user_role == UserRole.EMPLOYEE and request.user.employee_role == EmployeeRole.DOCTOR))


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in ['GET', 'HEAD', 'OPTIONS']
