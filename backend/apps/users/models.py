from django.contrib.auth.models import AbstractUser
from django.db import models
from cloudinary.models import CloudinaryField
from .managers import UserManager


class Role(models.TextChoices):
    ADMIN = "Admin", "Quản trị viên"
    DOCTOR = "Doctor", "Bác sĩ"
    PATIENT = "Patient", "Bệnh nhân"
    STAFF = "Staff", "Nhân viên y tế"


class Gender(models.TextChoices):
    MALE = "Male", "Nam"
    FEMALE = "Female", "Nữ"
    OTHER = "Other", "Khác"


class User(AbstractUser):
    username = None
    email = models.EmailField(max_length=100, unique=True)

    avatar = CloudinaryField(
        default='https://res.cloudinary.com/dam6k8ezg/image/upload/v1764155710/defaultAvatar_l5nyci.jpg', blank=True,
        null=True)
    phone_number = models.CharField(max_length=10, unique=True, null=True, blank=True)
    gender = models.CharField(max_length=6, choices=Gender.choices, default=Gender.OTHER)
    address = models.TextField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    updated_date = models.DateTimeField(auto_now=True)

    role = models.CharField(max_length=7, choices=Role.choices, null=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    def __str__(self):
        return self.email


class PatientProfile(models.Model):
    user = models.OneToOneField(User, related_name='patient_profile', on_delete=models.CASCADE, primary_key=True)

class DoctorProfile(models.Model):
    user = models.OneToOneField(User, related_name='doctor_profile', on_delete=models.CASCADE, primary_key=True)

class StaffProfile(models.Model):
    user = models.OneToOneField(User, related_name='staff_profile', on_delete=models.CASCADE, primary_key=True)
