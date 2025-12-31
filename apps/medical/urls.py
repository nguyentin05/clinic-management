from clinic_management.urls import router
from apps.medical.views import TestOrderView

router.register('test-orders', TestOrderView, basename='test-orders')

urlpatterns = [

]