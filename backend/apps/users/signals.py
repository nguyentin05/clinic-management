from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.users.models import User, UserRole, PatientProfile, DoctorProfile, EmployeeRole, NurseProfile, \
    PharmacistProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.user_role == UserRole.PATIENT:
            PatientProfile.objects.create(user=instance)

        elif instance.user_role == UserRole.EMPLOYEE:
            if instance.employee_role == EmployeeRole.DOCTOR:
                DoctorProfile.objects.create(user=instance)
            elif instance.employee_role == EmployeeRole.NURSE:
                NurseProfile.objects.create(user=instance)
            elif instance.employee_role == EmployeeRole.PHARMACIST:
                PharmacistProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if instance.user_role == UserRole.PATIENT:
        instance.patient_profile.save()