from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from apps.clinic.models import Appointment, AppointmentStatus
from apps.notifications.models import Notification
from apps.notifications.services import AppointmentNotifications

#chay 24/7
@shared_task
def send_appointment_reminders():
    now = timezone.now()

    # Lịch hẹn trong 2 giờ tới
    check_time = now + timedelta(hours=2)
    appointments = Appointment.objects.filter(
        date=check_time.date(),
        start_time__hour=check_time.hour,
        status=AppointmentStatus.CONFIRMED
    )

    for appointment in appointments:
        AppointmentNotifications.notify_reminder(appointment)

@shared_task
def cleanup_notifications():
    month = timezone.now() - timedelta(days=30)

    return Notification.objects.filter(is_read=True, read_at__lt=month).delete()