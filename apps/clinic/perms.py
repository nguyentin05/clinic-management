from rest_framework.permissions import BasePermission

class IsOwnerAppointment(BasePermission):
    def has_object_permission(self, request, view, appointment):
        return appointment.patient == request.user or appointment.doctor == request.user

class IsOwnerSchedule(BasePermission):
    def has_object_permission(self, request, view, schedule):
        return schedule.employee == request.user