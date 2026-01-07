from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.clinic.models import Appointment
from apps.notifications.services import AppointmentNotifications


@receiver(post_save, sender=Appointment)
def create_appointment(sender, instance, created, **kwargs):
    if created:
        AppointmentNotifications.notify_created(instance)

    if hasattr(instance, '_old_status'):
        old_status = instance._old_status
        new_status = instance.status

        if new_status == 'CANCELLED':
            AppointmentNotifications.notify_cancelled(instance)
        elif new_status == 'COMPLETED':
            AppointmentNotifications.notify_completed(instance)
        elif old_status == 'PENDING' and new_status == 'CONFIRMED':
            AppointmentNotifications.notify_confirmed(instance)
        elif old_status == 'CONFIRMED' and new_status == 'IN_PROCESS':
            AppointmentNotifications.notify_started(instance)


@receiver(pre_save, sender=Appointment)
def check_status_appointment(sender, instance, **kwargs):
    if instance.pk:
        old_instance = Appointment.objects.get(pk=instance.pk)
        #nếu có đổi trạng thái thì lưu tạm oldstatus để ss
        if old_instance.status != instance.status:
            instance._old_status = old_instance.status