from datetime import timedelta

from cloudinary.models import CloudinaryField
from django.db import models
from ckeditor.fields import RichTextField


class DayOfWeek(models.IntegerChoices):
    MONDAY = 0, 'Thứ 2'
    TUESDAY = 1, 'Thứ 3'
    WEDNESDAY = 2, 'Thứ 4'
    THURSDAY = 3, 'Thứ 5'
    FRIDAY = 4, 'Thứ 6'
    SATURDAY = 5, 'Thứ 7'
    SUNDAY = 6, 'Chủ nhật'


class AppointmentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Chờ xác nhận'
    CONFIRMED = 'CONFIRMED', 'Đã xác nhận'
    IN_PROCESS = 'IN_PROCESS', 'Đang khám'
    COMPLETED = 'COMPLETED', 'Hoàn thành'
    CANCELLED = 'CANCELLED', 'Đã hủy'


class Shift(models.TextChoices):
    MORNING = 'MORNING', 'Sáng (6:00 - 12:00)'
    AFTERNOON = 'AFTERNOON', 'Chiều (12:00 - 18:00)'
    EVENING = 'EVENING', 'Tối (18:00 - 23:00)'
    NIGHT = 'NIGHT', 'Khuya (0:00 - 6:00)'
    OTHER = 'OTHER', 'Khác'


class AppointmentType(models.TextChoices):
    ONLINE = 'ONLINE', 'Tư vấn trực tuyến'
    OFFLINE = 'OFFLINE', 'Khám tại phòng khám'


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
    duration = models.IntegerField(default=30)
    image = CloudinaryField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.specialty.name}"


class WorkSchedule(BaseModel):
    employee = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='work_schedules')

    week_start = models.DateField()
    week_end = models.DateField()

    date = models.DateField()

    day_of_week = models.IntegerField(choices=DayOfWeek.choices)

    start_time = models.TimeField()
    end_time = models.TimeField()

    shift = models.CharField(max_length=20, choices=Shift.choices, blank=True)

    is_appointable = models.BooleanField(default=True)

    class Meta:
        unique_together = ['employee', 'day_of_week', 'start_time', 'week_start']

    # tự tính todate
    def save(self, *args, **kwargs):
        if self.week_start and not self.week_end:
            self.week_end = self.week_start + timedelta(days=6)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.get_day_of_week_display()} ({self.start_time}-{self.end_time})"


class Room(BaseModel):
    name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


class Appointment(BaseModel):
    doctor = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='doctor_appointments')
    patient = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='patient_appointments', null=True,
                                blank=True)

    services = models.ManyToManyField(Service, related_name='appointments')

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    type = models.CharField(max_length=10, choices=AppointmentType.choices, null=True, blank=True)

    status = models.CharField(max_length=20, choices=AppointmentStatus.choices, default=AppointmentStatus.PENDING)

    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments')

    meeting_link = models.URLField(max_length=500, null=True, blank=True)

    patient_note = models.TextField(blank=True)

    doctor_note = models.TextField(blank=True)

    confirmed_date = models.DateTimeField(null=True, blank=True)

    total_price = models.DecimalField(max_digits=12, decimal_places=0, default=0)

    work_schedule = models.ForeignKey(WorkSchedule, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='appointments')

    reason = models.TextField(blank=True)

    deleted_date = models.DateTimeField(null=True, blank=True)

    completed_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Hẹn: {self.doctor.get_full_name()}: {self.date} ({self.start_time} - {self.end_time})"

    class Meta:
        indexes = [
            models.Index(fields=['doctor', 'date', 'status']),
            models.Index(fields=['patient', 'date']),
            models.Index(fields=['date', 'start_time']),
        ]
