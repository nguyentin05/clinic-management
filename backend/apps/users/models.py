import datetime

from django.contrib.auth.models import AbstractUser
from django.db import models
from cloudinary.models import CloudinaryField
from .managers import UserManager
from apps.clinic.models import Specialty


class UserRole(models.TextChoices):
    ADMIN = "Admin", "Quản trị viên"
    PATIENT = "Patient", "Bệnh nhân"
    EMPLOYEE = "Employee", "Nhân viên"


class EmployeeRole(models.TextChoices):
    DOCTOR = "Doctor", "Bác sĩ"
    NURSE = "Nurse", "Y tá"
    PHARMACIST = "Pharmacist", "Dược sĩ"


class Gender(models.TextChoices):
    MALE = "Male", "Nam"
    FEMALE = "Female", "Nữ"
    OTHER = "Other", "Khác"


class BloodType(models.TextChoices):
    A = 'A', 'A'
    B = 'B', 'B'
    AB = 'AB', 'AB'
    O = 'O', 'O'


class User(AbstractUser):
    user_role = models.CharField(max_length=20, choices=UserRole.choices)
    employee_role = models.CharField(max_length=20, choices=EmployeeRole.choices, null=True, blank=True)

    username = None
    email = models.EmailField(max_length=100, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    avatar = CloudinaryField(null=True)
    address = models.TextField(blank=True)

    employee_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    hire_date = models.DateField(null=True, blank=True)

    updated_date = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    def save(self, *args, **kwargs):
        if self.user_role != UserRole.EMPLOYEE:
            self.employee_role = None
        elif self.user_role == UserRole.EMPLOYEE and not self.employee_role:
            raise ValueError('Chưa có chức vụ cụ thể cho nhân viên')

        super().save(*args, **kwargs)

    def get_full_role(self):
        if self.user_role == UserRole.EMPLOYEE:
            return f'{self.user_role} - {self.employee_role}'
        return f'{self.user_role}'

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_full_role()})"


class PatientProfile(models.Model):
    user = models.OneToOneField(User, related_name='patient_profile', on_delete=models.CASCADE, primary_key=True)

    patient_code = models.CharField(max_length=20, unique=True)
    blood_type = models.CharField(max_length=5, choices=BloodType.choices, null=True, blank=True)
    allergies = models.TextField(blank=True)
    chronic_diseases = models.TextField(blank=True)
    medical_history = models.TextField(blank=True)
    insurance_number = models.CharField(max_length=50, null=True, blank=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    registered_date = models.DateField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.patient_code:
            self.patient_code = f'BN{datetime.date.today().year}{self.pk:06d}'

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient_code} - {self.user.get_full_name()}"


class EmployeeBaseProfile(models.Model):
    salary = models.DecimalField(max_digits=15, decimal_places=0, default=0)
    degree = models.CharField(max_length=100, null=True, blank=True)
    experience_years = models.IntegerField(default=0)

    class Meta:
        abstract = True


class DoctorProfile(EmployeeBaseProfile):
    user = models.OneToOneField(User, related_name='doctor_profile', on_delete=models.CASCADE, primary_key=True)

    specialty = models.ForeignKey(Specialty, on_delete=models.SET_NULL, null=True, related_name='doctors')
    doctor_license = models.CharField(max_length=50, unique=True, null=True, blank=True)
    bio = models.TextField(blank=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    total_reviews = models.IntegerField(default=0)
    total_patients = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"BS. {self.user.get_full_name()} - {self.specialty}"


class NurseProfile(EmployeeBaseProfile):
    user = models.OneToOneField(User, related_name='nurse_profile', on_delete=models.CASCADE, primary_key=True)
    nurse_license = models.CharField(max_length=50, unique=True, null=True, blank=True)

    def __str__(self):
        return f"YT. {self.user.get_full_name()}"


class PharmacistProfile(EmployeeBaseProfile):
    user = models.OneToOneField(User, related_name='pharmacist_profile', on_delete=models.CASCADE, primary_key=True)
    pharmacist_license = models.CharField(max_length=50, unique=True, null=True, blank=True)

    def __str__(self):
        return f"DS. {self.user.get_full_name()}"
