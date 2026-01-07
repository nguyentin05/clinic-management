from ckeditor.fields import RichTextField
from django.db import models


class TestStatus(models.TextChoices):
    REQUESTED = 'REQUESTED', 'Đã chỉ định'
    PROCESSING = 'PROCESSING', 'Đang thực hiện'
    COMPLETED = 'COMPLETED', 'Đã có kết quả'
    CANCELLED = 'CANCELLED', 'Đã hủy'


class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class MedicalRecord(models.Model):
    appointment = models.OneToOneField('clinic.Appointment', on_delete=models.CASCADE, related_name='medical_record',
                                       primary_key=True)

    symptoms = models.TextField(blank=True)
    diagnosis = models.TextField(blank=True)
    treatment_plan = models.TextField(blank=True)

    def __str__(self):
        return f"Bệnh án - {self.appointment}"


class TestOrder(BaseModel):
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='test_orders')

    service = models.ForeignKey('clinic.Service', on_delete=models.PROTECT, related_name='test_orders')

    nurse = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='confirmed_tests')

    result = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=TestStatus.choices, default=TestStatus.REQUESTED)

    note = models.TextField(blank=True)

    confirmed_date = models.DateTimeField(null=True, blank=True)

    reason = models.TextField(blank=True)

    deleted_date = models.DateTimeField(null=True, blank=True)

    deleted_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='deleted_tests')

    completed_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.service.name} - {self.medical_record.appointment.patient.get_full_name()}"
