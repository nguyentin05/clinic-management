from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema, no_body
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.clinic import paginators
from apps.clinic.models import Specialty, Service, WorkSchedule, Appointment, AppointmentType, AppointmentStatus, Room
from apps.clinic.perms import IsOwnerAppointment, IsPatient
from apps.clinic.serializers import SpecialtySerializer, ServiceSerializer, WorkScheduleSerializer, \
    RegisterScheduleSerializer, CreateAppointmentSerializer, AppointmentDetailSerializer, AppointmentSerializer, \
    ConfirmAppointmentSerializer, RoomSerializer, StartAppointmentSerializer
from apps.medical.models import MedicalRecord, TestOrder
from apps.medical.serializers import MedicalRecordSerializer, TestOrderSerializer


def get_monday_of_week(date):
    return date - timedelta(days=date.weekday())


class SpecialtyView(viewsets.ViewSet, generics.ListAPIView):
    queryset = Specialty.objects.filter(active=True)
    serializer_class = SpecialtySerializer

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

    def get_queryset(self):
        query = self.queryset

        q = self.request.query_params.get('q')
        if q:
            query = query.filter(name__icontains=q)

        return query


class WorkScheduleView(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'register_schedule':
            return RegisterScheduleSerializer
        return WorkScheduleSerializer

    def get_queryset(self):
        return WorkSchedule.objects.filter(
            employee=self.request.user,
            active=True
        ).order_by('day_of_week', 'start_time')

    @action(methods=['get'], detail=False, url_path='current-schedule')
    def get_current_schedule(self, request):
        today = timezone.now().date()
        current_monday = get_monday_of_week(today)

        schedules = self.get_queryset().filter(from_date=current_monday)

        data = self.get_serializer(schedules, many=True).data

        return Response({
            "mode": "view",
            "week_start": current_monday,
            "week_end": current_monday + timedelta(days=6),
            "schedules": data
        }, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='next-schedule')
    def get_next_schedule(self, request):
        today = timezone.now().date()
        next_monday = get_monday_of_week(today) + timedelta(days=7)

        schedules = self.get_queryset().filter(from_date=next_monday)

        data = self.get_serializer(schedules, many=True).data

        current_weekday = timezone.now().weekday()

        mode = "view" if current_weekday > 4 else "edit"

        return Response({
            "mode": mode,
            "week_start": next_monday,
            "week_end": next_monday + timedelta(days=6),
            "schedules": data
        }, status=status.HTTP_200_OK)

    @action(methods=['put'], detail=False, url_path='register-schedule')
    def register_schedule(self, request):
        user = request.user
        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        schedules = serializer.save()  # list/queryset

        week_start = serializer.validated_data['week_start']

        data = WorkScheduleSerializer(schedules, many=True).data

        return Response({
            "mode": 'edit',
            "week_start": week_start,
            "week_end": week_start + timedelta(days=6),
            "schedules": data
        }, status=status.HTTP_200_OK)


# chưa phân quyền chi tiết
class AppointmentView(viewsets.ViewSet, generics.ListAPIView, generics.CreateAPIView, generics.RetrieveAPIView):
    queryset = Appointment.objects.filter(active=True)
    pagination_class = paginators.AppointmentPaginator

    def get_permissions(self):
        if self.action == "create":
            return [IsPatient]
        return [IsOwnerAppointment]

    def get_serializer_class(self):
        if self.action == "create":
            return CreateAppointmentSerializer
        if self.action == "list":
            return AppointmentSerializer
        return AppointmentDetailSerializer

    def get_queryset(self):
        query = self.queryset
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

    @swagger_auto_schema(operation_description='Tạo lịch hẹn của bệnh nhân',
                         responses={status.HTTP_201_CREATED: AppointmentDetailSerializer()})
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        appointment = serializer.save()

        return Response(AppointmentDetailSerializer(appointment).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(operation_description='Xác nhận lịch hẹn', request_body=ConfirmAppointmentSerializer(),
                         responses={status.HTTP_200_OK: AppointmentDetailSerializer()})
    @action(methods=['patch'], detail=True, url_path='confirm')
    def confirm_appointment(self, request, pk):
        appointment = self.get_object()

        serializer = ConfirmAppointmentSerializer(appointment, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(AppointmentDetailSerializer(appointment).data, status=status.HTTP_200_OK)

    # tìm các phòng còn trống
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

        return Response(RoomSerializer(available_rooms, many=True).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(operation_description='Xác nhận lịch hẹn', request_body=no_body,
                         responses={status.HTTP_200_OK: AppointmentDetailSerializer()})
    @action(methods=['patch'], detail=True, url_path='start')
    def start_appointment(self, request, pk):
        appointment = self.get_object()

        serializer = StartAppointmentSerializer(appointment, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(AppointmentDetailSerializer(appointment).data, status=status.HTTP_200_OK)

    @action(methods=['get', 'patch'], detail=True, url_path='medical-record')
    def get_medical_record(self, request, pk):
        appointment = self.get_object()

        if appointment.status not in [AppointmentStatus.IN_PROCESS, AppointmentStatus.COMPLETED]:
            return Response('Cuộc hẹn chưa được bắt đầu.', status=status.HTTP_400_BAD_REQUEST)

        # tìm hs bệnh án nếu ko thấy trả về 404 luôn
        medical_record = get_object_or_404(MedicalRecord, appointment=appointment)

        if request.method == 'patch':
            serializer = MedicalRecordSerializer(medical_record, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return Response(MedicalRecordSerializer(medical_record).data, status=status.HTTP_200_OK)

    @action(methods=['get', 'post'], detail=True, url_path='test-orders')
    def get_test_orders(self, request, pk):
        appointment = self.get_object()

        if appointment.status not in [AppointmentStatus.IN_PROCESS, AppointmentStatus.COMPLETED]:
            return Response('Cuộc hẹn chưa được bắt đầu.', status=status.HTTP_400_BAD_REQUEST)

        medical_record = get_object_or_404(MedicalRecord, appointment=appointment)

        TestOrder.objects.filter(medical_record=medical_record)

        if request.method == 'post':
            serializer = TestOrderSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            test_order = serializer.save(medical_record=medical_record)
            return Response(TestOrderSerializer(test_order).data, status=status.HTTP_201_CREATED)

        test_orders = TestOrder.objects.filter(medical_record=medical_record)

        return Response(TestOrderSerializer(test_orders, many=True).data, status=status.HTTP_200_OK)