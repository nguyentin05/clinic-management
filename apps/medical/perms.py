from rest_framework.permissions import BasePermission


class IsOwnerTestOrderNurse(BasePermission):
    def has_object_permission(self, request, view, test):
        return test.nurse == request.user

class IsOwnerTestOrderDoctorOrNurse(IsOwnerTestOrderNurse):
    def has_object_permission(self, request, view, test):
        return super().has_object_permission(request, view, test) or test.medical_record.appointment.doctor == request.user

class IsOwnerTestOrder(IsOwnerTestOrderDoctorOrNurse):
    def has_object_permission(self, request, view, test):
        return super().has_object_permission(request, view, test) or test.medical_record.appointment.patient == request.user