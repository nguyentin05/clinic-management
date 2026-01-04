from cloudinary.models import CloudinaryField
from django.db import models


class MedicineUnit(models.TextChoices):
    BOX = 'BOX', 'Hộp'
    BOT = 'BOT', 'Chai'
    AMP = 'AMP', 'Ống tiêm'
    PAK = 'PAK', 'Gói'
    TUB = 'TUB', 'Tuýp'


class ImportReceiptStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Nháp'
    COMPLETED = 'COMPLETED', 'Đã nhập kho'
    CANCELED = 'CANCELED', 'Đã hủy'


class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class Prescription(BaseModel):
    appointment = models.OneToOneField('clinic.Appointment', on_delete=models.CASCADE, related_name='prescription')
    note = models.TextField(blank=True)

    def __str__(self):
        return f"Đơn thuốc - {self.appointment}"

class MedicineCategory(BaseModel):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Medicine(BaseModel):
    name = models.CharField(max_length=255, db_index=True)
    category = models.ForeignKey('MedicineCategory', on_delete=models.SET_NULL, null=True)
    unit = models.CharField(max_length=50, choices=MedicineUnit.choices, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    current_stock = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    image = CloudinaryField(null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

class PrescriptionDetail(BaseModel):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT, related_name='details')
    quantity = models.IntegerField(default=1)
    dosage = models.CharField(max_length=255)  # lieu luong

    def __str__(self):
        return f"{self.medicine} ({self.quantity})"


class DispenseLog(BaseModel):
    pharmacist = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    prescription = models.ForeignKey(Prescription, on_delete=models.PROTECT, related_name='dispense_logs')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.IntegerField()

class ImportReceipt(BaseModel):
    pharmacist = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    note = models.TextField(blank=True)
    status = models.CharField(max_length=20,choices=ImportReceiptStatus.choices,default=ImportReceiptStatus.DRAFT)

    def __str__(self):
        return f"Phiếu nhập {self.id} - {self.status}"


class ImportDetail(models.Model):
    receipt = models.ForeignKey(ImportReceipt, on_delete=models.CASCADE, related_name='details')
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    quantity = models.IntegerField(default=1)
    cost = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.medicine.name} - SL: {self.quantity}"


class DailyInventorySnapshot(models.Model):
    date = models.DateField(db_index=True)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, db_index=True)
    opening_quantity = models.IntegerField(default=0)
    import_quantity = models.IntegerField(default=0)
    export_quantity = models.IntegerField(default=0)
    closing_quantity = models.IntegerField(default=0)

    class Meta:
        unique_together = ('date', 'medicine')

    def __str__(self):
        return f"{self.date} - {self.medicine.name}"