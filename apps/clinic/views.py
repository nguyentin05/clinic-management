from datetime import timedelta
from django.db.models import Q, Avg, Count
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema, no_body
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.clinic import paginators
from apps.clinic.models import Specialty, Service, WorkSchedule, Appointment, AppointmentType, AppointmentStatus, Room, \
    Review
from apps.clinic.perms import IsOwnerAppointment, IsOwnerSchedule
from apps.clinic.serializers import SpecialtySerializer, ServiceSerializer, WorkScheduleSerializer, \
    RegisterScheduleSerializer, CreateAppointmentSerializer, AppointmentDetailSerializer, AppointmentSerializer, \
    ConfirmAppointmentSerializer, RoomSerializer, StartAppointmentSerializer, CancelAppointmentSerializer, \
    AppointmentStateSerializer, CompleteAppointmentSerializer, CreateReviewSerializer
from apps.clinic.utils import get_monday_of_week, param_q, schedule_custom_response, param_to_date, param_week_start, \
    param_status
from apps.medical.models import MedicalRecord, TestOrder
from apps.medical.serializers import MedicalRecordSerializer, TestOrderSerializer, TestOrderDetailSerializer
from apps.pharmacy.models import Prescription
from apps.pharmacy.serializers import PrescriptionSerializer
from apps.users.perms import IsEmployee, IsDoctorOrPatient, IsPatient, IsDoctor


class SpecialtyView(viewsets.ViewSet, generics.ListAPIView):
    queryset = Specialty.objects.filter(active=True)
    serializer_class = SpecialtySerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Lấy danh sách tất cả chuyên khoa đang hoạt động",
        responses={200: SpecialtySerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description='Lấy danh sách dịch vụ thuộc chuyên khoa (Hỗ trợ phân trang)',
        responses={200: ServiceSerializer(many=True)}
    )
    @action(methods=['get'], detail=True, url_path='services')
    def get_services(self, request, pk):
        services = self.get_object().services.filter(active=True)

        p = paginators.ServicePaginator()
        page = p.paginate_queryset(services, self.request)

        if page is not None:
            serializer = ServiceSerializer(page, many=True)
            return p.get_paginated_response(serializer.data)

        return Response(ServiceSerializer(services, many=True).data, status=status.HTTP_200_OK)


class ServiceView(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView):
    queryset = Service.objects.filter(active=True)
    serializer_class = ServiceSerializer
    pagination_class = paginators.ServicePaginator
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        manual_parameters=[param_q],
        operation_description="Tra cứu danh sách dịch vụ y tế (Có thể tìm kiếm theo tên)"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Xem chi tiết thông tin một dịch vụ",
        responses={200: ServiceSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self):
        query = self.queryset

        q = self.request.query_params.get('q')
        if q:
            query = query.filter(name__icontains=q)

        return query


class WorkScheduleView(viewsets.GenericViewSet):
    permission_classes = [IsOwnerSchedule, IsEmployee]

    def get_serializer_class(self):
        if self.action == 'register_schedule':
            return RegisterScheduleSerializer
        return WorkScheduleSerializer

    def get_queryset(self):
        return WorkSchedule.objects.filter(
            employee=self.request.user,
            active=True
        ).order_by('day_of_week', 'start_time')

    @swagger_auto_schema(
        operation_description="Xem lịch làm việc của nhân viên trong tuần hiện tại",
        responses={200: schedule_custom_response}
    )
    @action(methods=['get'], detail=False, url_path='current-schedule')
    def get_current_schedule(self, request):
        today = timezone.now().date()
        current_monday = get_monday_of_week(today)

        schedules = self.get_queryset().filter(week_start=current_monday)

        data = self.get_serializer(schedules, many=True).data

        return Response({
            "mode": "view",
            "week_start": current_monday,
            "week_end": current_monday + timedelta(days=6),
            "schedules": data
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Xem lịch làm việc của nhân viên trong tuần kế tiếp",
        responses={200: schedule_custom_response}
    )
    @action(methods=['get'], detail=False, url_path='next-schedule')
    def get_next_schedule(self, request):
        today = timezone.now().date()
        next_monday = get_monday_of_week(today) + timedelta(days=7)

        schedules = self.get_queryset().filter(week_start=next_monday)

        data = self.get_serializer(schedules, many=True).data

        current_weekday = timezone.now().weekday()

        mode = "view" if current_weekday > 4 else "edit"

        return Response({
            "mode": mode,
            "week_start": next_monday,
            "week_end": next_monday + timedelta(days=6),
            "schedules": data
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Đăng ký hoặc cập nhật lịch làm việc",
        request_body=RegisterScheduleSerializer,
        responses={200: schedule_custom_response}
    )
    @action(methods=['put'], detail=False, url_path='register-schedule')
    def register_schedule(self, request):
        user = request.user
        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        schedules = serializer.save()

        week_start = serializer.validated_data['week_start']

        data = WorkScheduleSerializer(schedules, many=True).data

        return Response({
            "mode": 'edit',
            "week_start": week_start,
            "week_end": week_start + timedelta(days=6),
            "schedules": data
        }, status=status.HTTP_200_OK)


class AppointmentView(viewsets.ViewSet, generics.ListAPIView, generics.CreateAPIView, generics.RetrieveAPIView):
    queryset = Appointment.objects.filter(active=True)
    pagination_class = paginators.AppointmentPaginator

    def get_permissions(self):
        if self.action in ["list", "retrieve", 'cancel_appointment']:
            return [IsOwnerAppointment(), IsDoctorOrPatient()]
        if self.action == "create":
            return [IsPatient()]
        if self.action in ['get_available_rooms', 'complete_appointment', 'confirm_appointment', 'start_appointment']:
            return [IsOwnerAppointment(), IsDoctor()]
        if self.action in ['get_prescription', "get_test_orders", 'get_medical_record']:
            if self.request.method == 'GET':
                return [IsOwnerAppointment(), IsDoctorOrPatient()]
            return [IsOwnerAppointment(), IsDoctor()]
        return [IsOwnerAppointment()]

    def get_serializer_class(self):
        if self.action == "create":
            return CreateAppointmentSerializer
        if self.action == "list":
            return AppointmentSerializer
        if self.action == "confirm_appointment":
            return ConfirmAppointmentSerializer
        if self.action == "start_appointment":
            return StartAppointmentSerializer
        if self.action == "get_medical_record":
            return MedicalRecordSerializer
        if self.action == "get_test_orders":
            return TestOrderSerializer
        if self.action == "get_available_rooms":
            return RoomSerializer
        if self.action == "cancel_appointment":
            return CancelAppointmentSerializer
        if self.action == 'complete_appointment':
            return CompleteAppointmentSerializer
        if self.action == 'get_prescription':
            return PrescriptionSerializer
        if self.action == 'review':
            return CreateReviewSerializer
        return AppointmentDetailSerializer

    def get_queryset(self):
        query = self.queryset.select_related('doctor', 'patient', 'work_schedule', 'room') \
            .prefetch_related('services', 'services__specialty')

        user = self.request.user

        # tùy theo role mà query tìm appointment
        query = query.filter(Q(patient=user) | Q(doctor=user))

        s = self.request.query_params.get('status')
        if s:
            query = query.filter(status=s)

        from_date = self.request.query_params.get('week_start')
        if from_date:
            query = query.filter(date__gte=from_date)

        to_date = self.request.query_params.get('to_date')
        if to_date:
            query = query.filter(date__lte=to_date)

        return query.order_by('-created_date')

    @swagger_auto_schema(
        manual_parameters=[param_status, param_week_start, param_to_date],
        operation_description="Lấy danh sách lịch hẹn (Hỗ trợ lọc theo ngày và trạng thái)"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description='Xem chi tiết thông tin một lịch hẹn',
        responses={200: AppointmentDetailSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description='Bệnh nhân đặt lịch hẹn khám bệnh mới',
        responses={status.HTTP_201_CREATED: AppointmentDetailSerializer()}
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        appointment = serializer.save()

        return Response(AppointmentDetailSerializer(appointment).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_description='Bác sĩ xác nhận lịch hẹn (Chuyển trạng thái sang CONFIRMED)',
        request_body=ConfirmAppointmentSerializer,
        responses={status.HTTP_200_OK: AppointmentStateSerializer()}
    )
    @action(methods=['patch'], detail=True, url_path='confirm')
    def confirm_appointment(self, request, pk):
        appointment = self.get_object()

        serializer = self.get_serializer(appointment, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(AppointmentStateSerializer(appointment).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description='Gợi ý danh sách phòng trống phù hợp cho lịch hẹn',
        responses={status.HTTP_200_OK: RoomSerializer(many=True)}
    )
    @action(methods=['get'], detail=True, url_path='available-rooms')
    def get_available_rooms(self, request, pk):
        appointment = self.get_object()

        if appointment.type == AppointmentType.ONLINE:
            return Response([], status=status.HTTP_200_OK)

        busy_room_ids = Appointment.objects.filter(
            date=appointment.date,
            status__in=[AppointmentStatus.CONFIRMED, AppointmentStatus.IN_PROCESS],
            room__isnull=False,
            start_time__lt=appointment.end_time,
            end_time__gt=appointment.start_time
        ).exclude(
            id=appointment.id
        ).values_list('room_id', flat=True)

        available_rooms = Room.objects.filter(active=True).exclude(id__in=busy_room_ids)

        return Response(self.get_serializer(available_rooms, many=True).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description='Bác sĩ bắt đầu cuộc hẹn (Chuyển trạng thái sang IN_PROCESS)',
        request_body=no_body,
        responses={status.HTTP_200_OK: AppointmentStateSerializer()}
    )
    @action(methods=['patch'], detail=True, url_path='start')
    def start_appointment(self, request, pk):
        appointment = self.get_object()

        serializer = self.get_serializer(appointment, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(AppointmentStateSerializer(appointment).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        methods=['get'],
        operation_description='Xem hồ sơ bệnh án thuộc lịch hẹn này',
        responses={200: MedicalRecordSerializer()}
    )
    @swagger_auto_schema(
        methods=['patch'],
        operation_description='Cập nhật thông tin hồ sơ bệnh án',
        request_body=MedicalRecordSerializer,
        responses={200: MedicalRecordSerializer()}
    )
    @action(methods=['get', 'patch'], detail=True, url_path='medical-record')
    def get_medical_record(self, request, pk):
        appointment = self.get_object()

        medical_record = get_object_or_404(MedicalRecord, appointment=appointment)

        if request.method == 'PATCH':
            serializer = self.get_serializer(medical_record, data=request.data, partial=True,
                                             context={'appointment': appointment})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(self.get_serializer(medical_record).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        methods=['post'],
        operation_description='Bác sĩ chỉ định (tạo) xét nghiệm mới',
        request_body=TestOrderSerializer,
        responses={status.HTTP_201_CREATED: TestOrderDetailSerializer()}
    )
    @swagger_auto_schema(
        methods=['get'],
        operation_description='Lấy danh sách các chỉ định xét nghiệm của lịch hẹn',
        responses={status.HTTP_200_OK: TestOrderSerializer(many=True)}
    )
    @action(methods=['get', 'post'], detail=True, url_path='test-orders')
    def get_test_orders(self, request, pk):
        appointment = self.get_object()

        if appointment.status not in [AppointmentStatus.IN_PROCESS, AppointmentStatus.COMPLETED]:
            return Response({"message": 'Cuộc hẹn chưa được bắt đầu.'}, status=status.HTTP_400_BAD_REQUEST)

        medical_record = get_object_or_404(MedicalRecord, appointment=appointment)

        if request.method == 'POST':
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            test = serializer.save(medical_record=medical_record)

            return Response(TestOrderDetailSerializer(test).data, status=status.HTTP_201_CREATED)

        test_orders = TestOrder.objects.filter(medical_record=medical_record)

        return Response(self.get_serializer(test_orders, many=True).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        methods=['patch'],
        operation_description='Hủy lịch hẹn (Dành cho bệnh nhân/Bác sĩ)',
        request_body=CancelAppointmentSerializer,
        responses={status.HTTP_200_OK: AppointmentStateSerializer()}
    )
    @action(methods=['patch'], detail=True, url_path='cancel')
    def cancel_appointment(self, request, pk):
        appointment = self.get_object()

        serializer = self.get_serializer(appointment, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(AppointmentStateSerializer(appointment).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        methods=['patch'],
        operation_description='Hoàn thành lịch hẹn (Kết thúc khám)',
        request_body=no_body,
        responses={status.HTTP_200_OK: AppointmentStateSerializer()}
    )
    @action(methods=['patch'], detail=True, url_path='complete')
    def complete_appointment(self, request, pk):
        appointment = self.get_object()

        serializer = self.get_serializer(appointment, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(AppointmentStateSerializer(appointment).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        methods=['get'],
        operation_description='Xem chi tiết đơn thuốc đã kê',
        responses={status.HTTP_200_OK: PrescriptionSerializer()}
    )
    @swagger_auto_schema(
        methods=['post'],
        operation_description='Bác sĩ kê đơn thuốc mới',
        request_body=PrescriptionSerializer,
        responses={status.HTTP_201_CREATED: PrescriptionSerializer()}
    )
    @swagger_auto_schema(
        methods=['patch'],
        operation_description='Chỉnh sửa đơn thuốc hiện có',
        request_body=PrescriptionSerializer,
        responses={status.HTTP_200_OK: PrescriptionSerializer()}
    )
    @swagger_auto_schema(
        methods=['delete'],
        operation_description='Xóa đơn thuốc',
        responses={
            status.HTTP_204_NO_CONTENT: openapi.Schema(type=openapi.TYPE_STRING, description="Đã xóa thành công")}
    )
    @action(methods=['get', 'post', 'patch', 'delete'], detail=True, url_path='prescription')
    def get_prescription(self, request, pk):
        appointment = self.get_object()

        if request.method == 'POST':
            if hasattr(appointment, 'prescription'):
                return Response({"detail": "Đơn thuốc đã tồn tại."},
                                status=status.HTTP_400_BAD_REQUEST)

            serializer = self.get_serializer(data=request.data, context={'appointment': appointment})
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        prescription = get_object_or_404(Prescription, appointment=appointment)

        if request.method == 'PATCH':
            serializer = self.get_serializer(prescription, data=request.data, partial=True,
                                             context={'appointment': appointment})
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(serializer.data, status=status.HTTP_200_OK)

        if request.method == 'DELETE':
            prescription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(self.get_serializer(prescription).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        methods=['post'],
        operation_description='Bệnh nhân gửi đánh giá cho bác sĩ',
        request_body=CreateReviewSerializer,
        responses={
            status.HTTP_201_CREATED: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={'message': openapi.Schema(type=openapi.TYPE_STRING, example='Đánh giá thành công!')}
            )
        }
    )
    @action(methods=['post'], detail=True, url_path='review')
    def review(self, request, pk):
        appointment = get_object_or_404(Appointment, id=pk, active=True, patient=request.user)

        serializer = self.get_serializer(data=request.data, context={'appointment': appointment})
        serializer.is_valid(raise_exception=True)
        review = serializer.save()

        # cập nhật rating
        doctor = review.doctor

        stats = Review.objects.filter(doctor=doctor).aggregate(rating=Avg('rating'), total_reviews=Count('id'))

        doctor.doctor_profile.rating = round(stats['rating'], 1)
        doctor.doctor_profile.total_reviews = stats['total_reviews']
        doctor.doctor_profile.save()

        return Response({"message": "Đánh giá thành công!"}, status=status.HTTP_201_CREATED)
