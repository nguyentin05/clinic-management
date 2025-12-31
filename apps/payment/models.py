from django.db import models


class PaymentStatus(models.TextChoices):
    UNPAID = 'UNPAID', 'Chưa thanh toán'
    PAID = 'PAID', 'Đã thanh toán'
    REFUNDED = 'REFUNDED', 'Đã hoàn tiền'


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
    appointment = models.OneToOneField('clinic.Appointment', on_delete=models.CASCADE, related_name='payment')

    amount = models.DecimalField(max_digits=12, decimal_places=0)

    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, null=True, blank=True)

    paid_at = models.DateTimeField(null=True, blank=True)

    # Người thu tiền (Thường là Y tá/Thu ngân)
    cashier = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='collected_payments')

    def __str__(self):
        return f"Hóa đơn {self.id} - {self.total_amount} ({self.get_status_display()})"
