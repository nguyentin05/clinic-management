from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.users.models import User, Role, PatientProfile, DoctorProfile, StaffProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.role.__eq__(Role.PATIENT):
            PatientProfile.objects.create(user=instance)
        elif instance.role.__eq__(Role.DOCTOR):
            DoctorProfile.objects.create(user=instance)
        elif instance.role.__eq__(Role.STAFF):
            StaffProfile.objects.create(user=instance)