from rest_framework.permissions import BasePermission

class IsOwnerOnlinePayment(BasePermission):
    def has_object_permission(self, request, view, payment):
        return payment.patient == request.user

class IsOwnerPayment(IsOwnerOnlinePayment):
    def has_object_permission(self, request, view, payment):
        return super().has_object_permission(request, view, payment) and payment.patient == request.user