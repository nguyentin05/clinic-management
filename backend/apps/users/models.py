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

class BloodType(models.TextChoices):
    A = 'A', 'A'
    B = 'B', 'B'
    AB = 'AB', 'AB'
    O = 'O', 'O'

class Specialty(models.TextChoices):
    GENERAL_PRACTICE = 'General practice', 'Đa khoa'
    CARDIOLOGIST = 'Cardiologist', 'Tim mạch'
    DERMATOLOGIST = 'Dermatologist', 'Gia liễu'
    OPHTHALMOLOGY = 'Ophthalmology', 'Mắt'
    PEDIATRICIAN = 'Pediatrician', 'Nhi khoa'


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
    blood_type = models.CharField(max_length=2, choices=BloodType.choices, null=True, blank=True)
    allergies = models.TextField(null=True, blank=True)
    weight = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    medical_history = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Hồ sơ bệnh nhân: {self.user.get_full_name()}"

class DoctorProfile(models.Model):
    user = models.OneToOneField(User, related_name='doctor_profile', on_delete=models.CASCADE, primary_key=True)
    salary = models.FloatField(null=True)
    specialty = models.CharField(max_length=30, choices=Specialty.choices, null=False)
    experience_years = models.IntegerField(default=0)
    license_number = models.CharField(max_length=50, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=0, default=0)

    def __str__(self):
        return f"Hồ sơ bác sĩ: {self.user.get_full_name()}"

class StaffProfile(models.Model):
    user = models.OneToOneField(User, related_name='staff_profile', on_delete=models.CASCADE, primary_key=True)
    salary = models.FloatField(null=True)
