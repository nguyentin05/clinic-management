from django.urls import path, include
from apps.payment.views import PaymentViewSet
from clinic_management.urls import router

router.register('payments', PaymentViewSet, basename='payments')

urlpatterns = [

]
