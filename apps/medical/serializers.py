from rest_framework import serializers

from apps.clinic.models import Service
from apps.medical.models import MedicalRecord, TestOrder, TestStatus
from apps.users.models import EmployeeRole


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
        fields = ['id', 'created_date', 'updated_date', 'service_id', 'service_name',
                  'nurse', 'result', 'status', 'status_display', 'note']
        read_only_fields = ['id', 'created_date', 'updated_date', 'nurse', 'result_text', 'status']

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user
        instance = self.instance

        if instance:
            if user.employee_role == EmployeeRole.NURSE:
                if instance.status not in [TestStatus.REQUESTED, TestStatus.PROCESSING]:
                    raise serializers.ValidationError(
                        {"status": "Xét nghiệm này không thể chỉnh sửa."}
                    )

                if 'service' in attrs:
                    raise serializers.ValidationError(
                        {"service": "Y tá không có quyền thay đổi dịch vụ."}
                    )

                if 'note' in attrs:
                    raise serializers.ValidationError(
                        {"note": "Y tá không được sửa ghi chú của bác sĩ."}
                    )

            elif instance and user.employee_role == EmployeeRole.DOCTOR:
                if instance.status != TestStatus.REQUESTED:
                    raise serializers.ValidationError(
                        {"status": "Xét nghiệm này không thể chỉnh sửa."}
                    )

                if 'result' in attrs:
                    raise serializers.ValidationError(
                        {"result": "Bác sĩ không được sửa kết quả xét nghiệm."}
                    )

        return attrs