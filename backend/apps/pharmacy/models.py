from django.db import models


class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class Prescription(BaseModel):
    appointment = models.OneToOneField('clinic.Appointment', on_delete=models.CASCADE, related_name='prescription')
    note = models.TextField(blank=True, null=True, help_text="Lời dặn chung cho đơn thuốc")

    def __str__(self):
        return f"Đơn thuốc - {self.appointment}"


class PrescriptionItem(BaseModel):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')

    medicine_name = models.CharField(max_length=255)
    quantity = models.IntegerField(default=1)
    dosage = models.CharField(max_length=255, help_text="Ví dụ: Sáng 1 viên, Tối 1 viên sau ăn")

    def __str__(self):
        return f"{self.medicine_name} ({self.quantity})"
