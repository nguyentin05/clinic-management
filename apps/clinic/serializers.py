from datetime import time, timedelta, datetime

from django.db import transaction
from django.db.models import F
from rest_framework import serializers
from django.utils import timezone

from apps.clinic.models import Specialty, Service, Appointment, WorkSchedule, AppointmentStatus, AppointmentType, Room, \
    Review
from apps.medical.models import MedicalRecord
from apps.users.serializers import DoctorInfoSerializer, PatientInfoSerializer


class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = ['id', 'name']


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'price', 'duration', 'image', 'specialty']

    def to_representation(self, instance):
        data = super().to_representation(instance)

        data['image'] = instance.image.url if instance.image else ''

        return data


# xem lich lam
class WorkScheduleSerializer(serializers.ModelSerializer):
    # tu dong cap nhat gio theo ca nen cho 2 trường này false
    start_time = serializers.TimeField(required=False)
    end_time = serializers.TimeField(required=False)
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    shift_display = serializers.CharField(source='get_shift_display', read_only=True)

    class Meta:
        model = WorkSchedule
        fields = ['id', 'day_of_week', 'day_of_week_display', 'start_time',
                  'end_time', 'shift', 'shift_display', 'is_appointable']
        read_only_fields = ['id', 'is_appointable']

    def validate(self, attrs):
        shift = attrs.get('shift')
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        # mapping tự động gán giờ theo ca
        STANDARD_SHIFTS = {
            'MORNING': (time(6, 0), time(12, 0)),
            'AFTERNOON': (time(12, 0), time(18, 0)),
            'EVENING': (time(18, 0), time(23, 0)),
            'NIGHT': (time(0, 0), time(6, 0)),
        }

        if shift in STANDARD_SHIFTS:
            t_start, t_end = STANDARD_SHIFTS[shift]
            attrs['start_time'] = t_start
            attrs['end_time'] = t_end

        elif shift == 'OTHER':
            if not start_time or not end_time:
                raise serializers.ValidationError('bắt buộc phải nhập giờ bắt đầu và giờ kết thúc với ca tùy chọn')

            if start_time >= end_time:
                raise serializers.ValidationError('Thời gian kết thúc phải sau thời gian bắt đầu.')

        return attrs


# đăng kí lịch làm
class RegisterScheduleSerializer(serializers.Serializer):
    week_start = serializers.DateField()
    schedules = WorkScheduleSerializer(many=True)

    # ràng buộc ngày gửi lên phải là t2
    def validate_week_start(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError('Không thể đăng ký lịch cho quá khứ.')

        if value.weekday() != 0:
            raise serializers.ValidationError('Ngày bắt đầu phải là thứ 2')

        return value

    def validate(self, attrs):
        if timezone.now().weekday() > 4:
            raise serializers.ValidationError('Đã hết hạn đăng ký lịch.')

        schedules = attrs.get('schedules', [])

        # sort lại lịch theo thứ tự
        schedules = sorted(
            schedules,
            key=lambda x: (x['day_of_week'], str(x['start_time']))
        )

        # kiểm tra coi các  ca có đè lên nhau ko
        for i in range(len(schedules) - 1):
            current = schedules[i]
            next = schedules[i + 1]

            if current['day_of_week'] == next['day_of_week']:
                current_end = current['end_time']
                next_start = next['start_time']

                if current_end > next_start:
                    raise serializers.ValidationError(
                        f"Lỗi trùng lịch vào ngày thứ {current['day_of_week'] + 2}: "
                        f"Ca {current['shift']} ({current['start_time']}-{current['end_time']}) "
                        f"bị trùng với ca {next['shift']} ({next['start_time']}-{next['end_time']})."
                    )

        return attrs

    # logic đăng kí lịch làm: lấy lịch cũ rồi ktra các booking có trong lịch cũ rồi ktra xem lịch mới có chứa booking đó ko
    @transaction.atomic
    def update(self, instance, validated_data):
        user = instance
        week_start = validated_data['week_start']
        schedules_data = validated_data['schedules']

        week_end = week_start + timezone.timedelta(days=6)

        old_schedules = WorkSchedule.objects.filter(
            employee=user,
            week_start=week_start
        )

        # ktra coi có cuộc hẹn nào bị đụng tới ko
        for old_schedule in old_schedules:
            date = week_start + timedelta(days=old_schedule.day_of_week)

            has_appointment = Appointment.objects.filter(
                doctor=user,
                date=date,
                status__in=['PENDING', 'CONFIRMED'],
                start_time__gte=old_schedule.start_time,
                end_time__lte=old_schedule.end_time
            ).first()

            if has_appointment:
                is_covered = False

                for shift in schedules_data:
                    if shift['day_of_week'] == old_schedule.day_of_week:
                        if (shift['start_time'] <= has_appointment.start_time and
                                shift['end_time'] >= has_appointment.end_time):
                            is_covered = True
                            break

                if not is_covered:
                    raise serializers.ValidationError(
                        f"KHÔNG THỂ SỬA/XÓA ca làm việc Thứ {old_schedule.day_of_week + 2} ({old_schedule.start_time}-{old_schedule.end_time}) "
                        f"vì lịch mới không bao phủ được cuộc hẹn lúc ({has_appointment.start_time} - {has_appointment.end_time}). "
                        f"Vui lòng đảm bảo ca làm việc mới phải bao trùm cuộc hẹn này."
                    )

        old_schedules.delete()
        schedules = []

        # hàm bulk_create ko gọi hàm save nên phải tự gán thằng todate
        for item_data in schedules_data:
            date = week_start + timedelta(days=item_data['day_of_week'])
            schedule = WorkSchedule(
                employee=user,
                week_start=week_start,
                week_end=week_end,
                date=date,
                active=True,
                **item_data
            )
            schedules.append(schedule)

        return WorkSchedule.objects.bulk_create(schedules)


# tạo lịch hẹn
class CreateAppointmentSerializer(serializers.ModelSerializer):
    service_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=True)

    class Meta:
        model = Appointment
        fields = ['doctor', 'service_ids', 'date', 'start_time', 'type', 'patient_note']

    def validate_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError('Không thể đặt lịch hẹn trong quá khứ.')

        # giới hạn 2 tuần: ngày hôm nay + số ngày tới chủ nhật và thêm 1 tuần
        max_date = timezone.now().date() + timedelta(days=6 - timezone.now().weekday()) + timedelta(days=7)
        if value > max_date:
            raise serializers.ValidationError('Chỉ có thể đặt lịch hẹn trước chủ nhật tuần sau.')

        return value

    def validate_service_ids(self, value):
        if not value:
            raise serializers.ValidationError('Phải chọn ít nhất một dịch vụ.')

        services = Service.objects.filter(id__in=value, active=True)

        if services.count() != len(value):
            raise serializers.ValidationError('dịch vụ không hợp lệ.')

        return value

    def validate(self, attrs):
        doctor = attrs.get('doctor')
        date = attrs.get('date')
        start_time = attrs.get('start_time')
        service_ids = attrs.get('service_ids')

        # tính tổng thời gian và tiền
        services = Service.objects.filter(id__in=service_ids)
        total_duration = sum(s.duration for s in services)
        total_price = sum(s.price for s in services)

        # tự động tính thời gian end
        start_dt = datetime.combine(date, start_time)
        end_dt = start_dt + timedelta(minutes=total_duration)
        end_time = end_dt.time()

        attrs['end_time'] = end_time
        attrs['services'] = services
        attrs['total_price'] = total_price

        # tìm ca làm phù hợp
        has_schedule = WorkSchedule.objects.filter(
            employee=doctor,
            week_start__lte=date,
            week_end__gte=date,
            day_of_week=date.weekday(),
            start_time__lte=start_time,
            end_time__gte=end_time,
            active=True
        ).first()

        if not has_schedule:
            raise serializers.ValidationError(
                f"Bác sĩ không có lịch làm việc vào thời gian này."
            )

        attrs['work_schedule'] = has_schedule
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        end_time = validated_data['end_time']
        services = validated_data.pop('services')
        patient = self.context['request'].user
        doctor = validated_data['doctor']
        date = validated_data['date']
        start_time = validated_data['start_time']

        # Xóa field input ảo
        validated_data.pop('service_ids')

        # tìm coi có kẹt lịch với lịch khác ko
        overlapping = Appointment.objects.filter(
            doctor=doctor,
            date=date,
            status__in=[AppointmentStatus.PENDING, AppointmentStatus.IN_PROCESS, AppointmentStatus.CONFIRMED],
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exists()

        if overlapping:
            raise serializers.ValidationError('Bác sĩ đã có lịch hẹn vào thời gian này.')

        appointment = Appointment.objects.create(
            patient=patient,
            status=AppointmentStatus.PENDING,
            **validated_data
        )
        appointment.services.set(services)

        return appointment


class AppointmentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display')
    type_display = serializers.CharField(source='get_type_display')

    class Meta:
        model = Appointment
        fields = ['id', 'date', 'start_time', 'end_time', 'type', 'type_display', 'status', 'status_display']


# xem chi tiết
class AppointmentDetailSerializer(AppointmentSerializer):
    doctor = DoctorInfoSerializer()
    patient = PatientInfoSerializer()
    services = ServiceSerializer(many=True)

    class Meta:
        model = AppointmentSerializer.Meta.model
        fields = AppointmentSerializer.Meta.fields + ['doctor', 'patient', 'services', 'room', 'meeting_link',
                                                      'patient_note', 'doctor_note', 'confirmed_date', 'created_date',
                                                      'deleted_date']


class AppointmentStateSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Appointment
        fields = ['id', 'status', 'status_display', 'updated_date', 'reason', 'deleted_date', 'confirmed_date',
                  'doctor_note', 'meeting_link', 'room']


# xác nhận
class ConfirmAppointmentSerializer(serializers.ModelSerializer):
    room = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.all(),
        required=False)
    doctor_note = serializers.CharField(required=False)

    class Meta:
        model = Appointment
        fields = ['id', 'room', 'doctor_note']

    def validate(self, attrs):
        appointment = self.instance

        if appointment.status != AppointmentStatus.PENDING:
            raise serializers.ValidationError('Không thể xác nhận lịch hẹn.')

        if appointment.date < timezone.now().date():
            raise serializers.ValidationError('Lịch đã quá hẹn.')

        if appointment.type == AppointmentType.OFFLINE and not attrs.get('room'):
            raise serializers.ValidationError('Lịch hẹn offline cần có số phòng khám.')

        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        instance.status = AppointmentStatus.CONFIRMED
        instance.confirmed_date = timezone.now()
        instance.doctor_note = validated_data['doctor_note']
        if instance.type == AppointmentType.OFFLINE:
            instance.room = validated_data['room']
            instance.meeting_link = None

        else:
            instance.room = None
            instance.meeting_link = 'https://meet.google.com/new-meeting-generated-by-system'
        instance.save()

        return instance


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'name']


class StartAppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = []

    def validate(self, attrs):
        appointment = self.instance

        if appointment.status != AppointmentStatus.CONFIRMED:
            raise serializers.ValidationError('Lịch hẹn phải ở trạng thái Đã xác nhận mới có thể bắt đầu khám.')

        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        instance.status = AppointmentStatus.IN_PROCESS
        instance.save()
        MedicalRecord.objects.get_or_create(appointment=instance)

        return instance


class CancelAppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ['reason']

    def validate(self, attrs):
        appointment = self.instance

        if appointment.status != AppointmentStatus.PENDING:
            raise serializers.ValidationError('Không thể hủy lịch hẹn.')

        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        instance.status = AppointmentStatus.CANCELLED
        instance.reason = validated_data['reason']
        instance.deleted_date = timezone.now()
        instance.save()

        return instance


class CompleteAppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = []

    def validate(self, attrs):
        appointment = self.instance

        if appointment.status != AppointmentStatus.IN_PROCESS:
            raise serializers.ValidationError('Lịch hẹn phải ở trạng thái đang diễn ra mới có thể hoàn thành cuộc hẹn')

        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        instance.status = AppointmentStatus.COMPLETED
        instance.save()
        profile = instance.doctor.doctor_profile
        profile.total_patients = F('total_patients') + 1
        profile.save()

        instance.refresh_from_db()
        return instance


class CreateReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'rating', 'comment', 'created_date']

    def validate(self, attrs):
        appointment = self.context.get('appointment')

        if appointment.status != AppointmentStatus.COMPLETED:
            raise serializers.ValidationError("Bạn chỉ có thể đánh giá khi buổi hẹn đã hoàn thành.")

        if hasattr(appointment, 'review'):
            raise serializers.ValidationError("Bạn đã đánh giá buổi hẹn này rồi")

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        appointment = self.context['appointment']

        review = Review.objects.create(
            appointment=appointment,
            doctor=appointment.doctor,
            patient=appointment.patient,
            **validated_data
        )
        return review
