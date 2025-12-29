from rest_framework import serializers

from apps.clinic.models import Service
from apps.medical.models import MedicalRecord, TestOrder


class MedicalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalRecord
        fields = ['symptoms', 'diagnosis', 'treatment_plan']

class TestOrderSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(), source='service', write_only=True
    )

    class Meta:
        model = TestOrder
        fields = [
            'id', 'created_date', 'updated_date',
            'service_id', 'service_name',
            'nurse', 'result_text', 'status', 'status_display', 'note'
        ]
        read_only_fields = ['id', 'created_date', 'updated_date', 'nurse', 'result_text', 'status']