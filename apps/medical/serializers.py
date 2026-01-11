from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.clinic.models import Service, AppointmentStatus
from apps.medical.models import MedicalRecord, TestOrder, TestStatus
from apps.users.models import EmployeeRole


class MedicalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalRecord
        fields = ['symptoms', 'diagnosis', 'treatment_plan']

    def validate(self, attrs):
        appointment = self.context.get('appointment')

        if appointment.status != AppointmentStatus.IN_PROCESS:
            raise serializers.ValidationError('Chỉ có thể sửa hồ sơ bệnh án ở trạng thái đang xử lý')

        return attrs


class TestOrderSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    service_id = serializers.PrimaryKeyRelatedField(queryset=Service.objects.filter(active=True), source='service',
                                                    write_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)

    class Meta:
        model = TestOrder
        fields = ['id', 'updated_date', 'service_id', 'service_name', 'status', 'status_display', 'note']
        read_only_fields = ['id', 'updated_date', 'status']
        extra_kwargs = {
            'note': {
                'write_only': True
            }
        }


# do cập nhật dùng chung nên phải phân rõ role và trạng thái
class TestOrderDetailSerializer(TestOrderSerializer):
    class Meta:
        model = TestOrderSerializer.Meta.model
        fields = TestOrderSerializer.Meta.fields + \
                 ['nurse', 'result', 'reason', 'deleted_by', 'deleted_date', 'completed_date']
        read_only_fields = TestOrderSerializer.Meta.read_only_fields + \
                           ['nurse', 'reason', 'deleted_by', 'deleted_date', 'completed_date']


class ConfirmTestOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestOrder
        fields = []

    def validate(self, attrs):
        if self.instance.status != TestStatus.REQUESTED:
            raise serializers.ValidationError('Không thể xác nhận xét nghiệm.')

        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        instance.status = TestStatus.PROCESSING
        instance.confirmed_date = timezone.now()
        instance.nurse = self.context['request'].user
        instance.save()

        return instance


class CancelTestOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestOrder
        fields = ['reason']

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user
        instance = self.instance

        if (user.employee_role == EmployeeRole.NURSE and instance.status != TestStatus.PROCESSING) \
                or (user.employee_role == EmployeeRole.DOCTOR and instance.status != TestStatus.REQUESTED):
            raise serializers.ValidationError("Xét nghiệm này không thể bị xóa.")

        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        instance.status = TestStatus.CANCELLED
        instance.active = False
        instance.reason = validated_data['reason']
        instance.deleted_date = timezone.now()
        instance.deleted_by = self.context['request'].user
        instance.save()

        return instance


class CompleteTestOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestOrder
        fields = []

    def validate(self, attrs):
        instance = self.instance

        if instance.status != TestStatus.PROCESSING:
            raise serializers.ValidationError("Chỉ có thể hoàn tất các xét nghiệm đang trong quá trình xử lý.")

        if not instance.result or not instance.result.strip():
            raise serializers.ValidationError("Vui lòng nhập kết quả xét nghiệm trước khi hoàn thành.")

        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        instance.status = TestStatus.COMPLETED
        instance.completed_date = timezone.now()
        instance.save()

        return instance


class UpdateTestOrderSerializer(serializers.ModelSerializer):
    service_id = serializers.PrimaryKeyRelatedField(queryset=Service.objects.filter(active=True), source='service',
                                                    required=False, write_only=True)

    class Meta:
        model = TestOrder
        fields = ['service_id', 'note', 'result']

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user
        instance = self.instance

        if user.employee_role == EmployeeRole.DOCTOR:
            if instance.status != TestStatus.REQUESTED:
                raise serializers.ValidationError("Xét nghiệm đã được xác nhận ko thể sửa")

            if 'result' in attrs:
                raise serializers.ValidationError("Bác sĩ không thể sửa kết quả xét nghiệm.")

        if user.employee_role == EmployeeRole.NURSE:
            if instance.status != TestStatus.PROCESSING:
                raise serializers.ValidationError("Y tá chỉ được nhập kết quả khi đang xử lý.")

            if 'service' in attrs or 'note' in attrs:
                raise serializers.ValidationError("Y tá không thể sửa dịch vụ hoặc ghi chú.")

        return attrs
