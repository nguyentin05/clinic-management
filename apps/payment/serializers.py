from rest_framework import serializers
from django.utils import timezone

from apps.payment.models import Payment, PaymentMethod


class PaymentSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source='get_method_display', read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'method', 'method_display', 'amount', 'is_paid', 'paid_date']


class PaymentDetailSerializer(PaymentSerializer):
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    nurse_name = serializers.CharField(source='nurse.get_full_name', read_only=True, allow_null=True)
    # liên kết với object liên quan tới thanh toán
    appointment_info = serializers.SerializerMethodField()
    prescription_info = serializers.SerializerMethodField()

    class Meta:
        model = PaymentSerializer.Meta.model
        fields = PaymentSerializer.Meta.fields + ['created_date', 'patient', 'patient_name',
                                                  'nurse', 'nurse_name', 'appointment', 'appointment_info',
                                                  'prescription', 'prescription_info', 'transaction_id']
        read_only_fields = ['id', 'created_date', 'patient', 'appointment', 'prescription']

    def get_appointment_info(self, obj):
        if obj.appointment:
            return {
                'id': obj.appointment.id,
                'date': obj.appointment.date,
                'doctor_name': obj.appointment.doctor.get_full_name()
            }
        return None

    def get_prescription_info(self, obj):
        if obj.get_prescription:
            return {
                'id': obj.get_prescription.id,
                'created_date': obj.get_prescription.created_date,
                'doctor_name': obj.get_prescription.appointment.doctor.get_full_name()
            }
        return None


# thanh toán gửi loại và return url
class OnlinePaymentSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(choices=['MOMO', 'STRIPE', 'VNPAY'])
    return_url = serializers.URLField(required=False)


# check status để xuất kết quả thanh toán
class PaymentStatusSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source='get_method_display', read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'is_paid', 'amount', 'paid_date', 'method', 'method_display', 'transaction_id']
