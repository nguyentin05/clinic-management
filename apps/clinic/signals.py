from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.clinic.models import Appointment, AppointmentStatus
from apps.notifications.services import AppointmentNotifications


@receiver(post_save, sender=Appointment)
def create_appointment(sender, instance, created, **kwargs):
    if created:
        AppointmentNotifications.notify_created(instance)

    if instance.tracker.has_changed('status'):
        new_status = instance.status
        old_status = instance.tracker.previous('status')

        if new_status == AppointmentStatus.CANCELLED:
            AppointmentNotifications.notify_cancelled(instance)
        elif new_status == AppointmentStatus.COMPLETED:
            AppointmentNotifications.notify_completed(instance)
        elif old_status == AppointmentStatus.PENDING and new_status == AppointmentStatus.CONFIRMED:
            AppointmentNotifications.notify_confirmed(instance)
        elif old_status == AppointmentStatus.CONFIRMED and new_status == AppointmentStatus.IN_PROCESS:
            AppointmentNotifications.notify_started(instance)
