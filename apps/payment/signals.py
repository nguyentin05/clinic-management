from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from django.db.models import Sum

from apps.clinic.models import Appointment, AppointmentStatus
from apps.notifications.services import PrescriptionNotifications, PaymentNotifications
from apps.payment.models import Payment


@receiver(post_save, sender=Appointment)
def create_appointment_payment(sender, instance, created, **kwargs):
    if instance.status == AppointmentStatus.COMPLETED:
        doctor_fee = instance.doctor.doctor_profile.consultation_fee
        #aggregate trả về từ điển nên lấy phải lấy key total mới đúng
        services_fee = instance.medical_record.test_orders.filter(deleted_at__isnull=True)\
                .aggregate(total=Sum('service__price'))['total']

        services_fee += instance.services.aggregate(total=Sum('price'))['total']

        total_amount = doctor_fee + services_fee

        Payment.objects.create(
            appointment=instance,
            patient=instance.patient,
            total_amount=total_amount,
            is_paid=False
        )

        instance.total_price = total_amount
        #Dùng update_fields để chỉ định đúng trường cập nhật để ko chạy lại signal
        instance.save(update_fields=['total_price'])

dispense_completed = Signal()

@receiver(dispense_completed)
def create_prescription_payment(sender, **kwargs):
    prescription = kwargs.get('prescription')

    Payment.objects.create(
        prescription=prescription,
        patient=prescription.appointment.patient,
        total_amount=kwargs.get('total_amount'),
        is_paid=False
    )
    #gửi thông báo luôn cho bệnh nhân
    PrescriptionNotifications.notify_conmpleted(prescription)

@receiver(post_save, sender=Payment)
def create_payment(sender, instance, created, **kwargs):
    if created:
        PaymentNotifications.notify_created(instance)