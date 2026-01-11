from django.db import models
from django.db.models import Q
from model_utils import FieldTracker


class PaymentMethod(models.TextChoices):
    CASH = 'CASH', 'Tiền mặt'
    BANKING = 'BANKING', 'Chuyển khoản'


class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class Payment(BaseModel):
    patient = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='payments')

    appointment = models.ForeignKey('clinic.Appointment', on_delete=models.SET_NULL, null=True, blank=True)

    prescription = models.ForeignKey('pharmacy.Prescription', on_delete=models.SET_NULL, null=True, blank=True)

    amount = models.DecimalField(max_digits=12, decimal_places=0)

    method = models.CharField(max_length=20, choices=PaymentMethod.choices, null=True, blank=True)

    nurse = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='collected_payments')

    is_paid = models.BooleanField(default=False)

    paid_date = models.DateTimeField(null=True, blank=True)

    transaction_id = models.CharField(max_length=255, blank=True, null=True)

    tracker = FieldTracker()

    class Meta:
        # ràng buộc phải thuộc 1 trong 2 loại
        constraints = [
            models.CheckConstraint(
                check=Q(appointment__isnull=False) | Q(prescription__isnull=False),
                name='payment_must_have_source'
            )
        ]
