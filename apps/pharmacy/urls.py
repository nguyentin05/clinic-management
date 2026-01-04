from apps.pharmacy.views import MedicineView, PrescriptionView, ImportReceiptView
from clinic_management.urls import router

router.register('medicines', MedicineView, basename='medicines')
router.register('prescriptions', PrescriptionView, basename='prescriptions')
router.register('import-receipts', ImportReceiptView, basename='import-receipts')

urlpatterns = [
]