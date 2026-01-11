from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from apps.medical.models import TestOrder, TestStatus
from apps.notifications.services import TestOrderNotifications


@receiver(post_save, sender=TestOrder)
def create_test_order(sender, instance, created, **kwargs):
    if created:
        TestOrderNotifications.notify_created(instance)

    if instance.tracker.has_changed('status'):
        new_status = instance.status

        if new_status == TestStatus.COMPLETED:
            TestOrderNotifications.notify_completed(instance)
        elif new_status == TestStatus.CANCELLED:
            TestOrderNotifications.notify_cancelled(instance)
        elif instance.tracker.previous('status') == TestStatus.REQUESTED and new_status == TestStatus.PROCESSING:
            TestOrderNotifications.notify_processing(instance)