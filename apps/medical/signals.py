from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from apps.medical.models import TestOrder
from apps.notifications.services import TestOrderNotifications


@receiver(post_save, sender=TestOrder)
def create_test_order(sender, instance, created, **kwargs):
    if created:
        TestOrderNotifications.notify_created(instance)

    if hasattr(instance, '_old_status'):
        old_status = instance._old_status
        new_status = instance.status

        if new_status == 'COMPLETED':
            TestOrderNotifications.notify_completed(instance)

        elif new_status == 'CANCELLED':
            TestOrderNotifications.notify_cancelled(instance)

        elif old_status == 'REQUESTED' and new_status == 'PROCESSING':
            TestOrderNotifications.notify_processing(instance)


@receiver(pre_save, sender=TestOrder)
def check_status_test_order(sender, instance, **kwargs):
    if instance.pk:
        old_instance = TestOrder.objects.get(pk=instance.pk)
        if old_instance.status != instance.status:
            instance._old_status = old_instance.status
