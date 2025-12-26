from cloudinary.models import CloudinaryField
from django.conf import settings
from django.db import models
from ckeditor.fields import RichTextField


class Status(models.TextChoices):
    PENDING = 'PENDING', 'Chờ xác nhận'
    CONFIRMED = 'CONFIRMED', 'Đã xác nhận'
    COMPLETED = 'COMPLETED', 'Đã khám xong'
    CANCELLED = 'CANCELLED', 'Đã hủy'


class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class Specialty(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class Service(BaseModel):
    specialty = models.ForeignKey(Specialty, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=255)
    description = RichTextField(null=True)
    price = models.DecimalField(max_digits=10, decimal_places=0)
    duration_minutes = models.IntegerField(default=15)
    image = CloudinaryField(
        default='https://res.cloudinary.com/dam6k8ezg/image/upload/v1764155710/defaultAvatar_l5nyci.jpg', blank=True,
        null=True)

    def __str__(self):
        return self.name

class Appointment(BaseModel):
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='patient')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='doctor')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True)
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    symptom = models.TextField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Lịch {self.id} - {self.date} - {self.patient.first_name}"