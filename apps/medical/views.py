from drf_yasg.utils import swagger_auto_schema, no_body
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.medical.models import TestOrder
from apps.medical.perms import IsOwnerTestOrder, IsOwnerTestOrderDoctorOrNurse, IsOwnerTestOrderNurse
from apps.medical.serializers import TestOrderSerializer, ConfirmTestOrderSerializer, TestOrderDetailSerializer, \
    CancelTestOrderSerializer, CompleteTestOrderSerializer, UpdateTestOrderSerializer
from apps.medical.ultis import param_test_status
from apps.users.perms import IsNurse


class TestOrderView(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView):
    queryset = TestOrder.objects.filter(active=True)

    def get_permissions(self):
        if self.action in ['list', 'confirm_test']:
            return [IsNurse()]
        if self.action == 'retrieve':
            return [IsOwnerTestOrder()]
        if self.action in ['cancel_test', 'update_test']:
            return [IsOwnerTestOrderDoctorOrNurse()]
        if self.action == 'complete_test':
            return [IsOwnerTestOrderNurse()]
        return [IsAuthenticated()]

    def get_queryset(self):
        query = self.queryset.select_related(
            'service', 'service__specialty', 'nurse', 'medical_record', 'medical_record__appointment',
            'medical_record__appointment__patient', 'medical_record__appointment__doctor'
        )

        s = self.request.query_params.get('status')
        if s:
            query = query.filter(status=s)

        return query.order_by('-created_date')

    def get_serializer_class(self):
        if self.action == 'confirm_test':
            return ConfirmTestOrderSerializer
        if self.action == 'list':
            return TestOrderSerializer
        if self.action == 'cancel_test':
            return CancelTestOrderSerializer
        if self.action == 'complete_test':
            return CompleteTestOrderSerializer
        if self.action == 'update_test':
            return UpdateTestOrderSerializer

        return TestOrderDetailSerializer

    @swagger_auto_schema(
        manual_parameters=[param_test_status],
        operation_description="Lấy danh sách các yêu cầu xét nghiệm (Dành cho Y tá)",
        responses={200: TestOrderSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Xem chi tiết phiếu chỉ định xét nghiệm",
        responses={200: TestOrderDetailSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description='Y tá xác nhận tiếp nhận phiếu xét nghiệm (Chuyển trạng thái sang IN_PROCESS)',
        request_body=no_body,
        responses={status.HTTP_200_OK: TestOrderDetailSerializer()}
    )
    @action(methods=['patch'], detail=True, url_path='confirm')
    def confirm_test(self, request, pk):
        test = self.get_object()

        serializer = self.get_serializer(test, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        test = serializer.save()

        return Response(TestOrderDetailSerializer(test).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description='Cập nhật thông tin phiếu xét nghiệm.\n\n'
                              '**Lưu ý:**\n'
                              '- **Bác sĩ:** Chỉ được cập nhật kết quả (result_file, result_text...)\n'
                              '- **Y tá:** Chỉ được cập nhật trạng thái hoặc ghi chú thực hiện.',
        request_body=UpdateTestOrderSerializer(),
        responses={status.HTTP_200_OK: TestOrderDetailSerializer()}
    )
    @action(methods=['patch'], detail=True, url_path='update')
    def update_test(self, request, pk):
        test = self.get_object()

        serializer = self.get_serializer(test, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        test = serializer.save()

        return Response(TestOrderDetailSerializer(test).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description='Hủy yêu cầu xét nghiệm (Dành cho Bác sĩ hoặc Y tá)',
        request_body=CancelTestOrderSerializer(),
        responses={status.HTTP_200_OK: TestOrderDetailSerializer()}
    )
    @action(methods=['patch'], detail=True, url_path='cancel')
    def cancel_test(self, request, pk):
        test = self.get_object()

        serializer = self.get_serializer(test, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        test = serializer.save()

        return Response(TestOrderDetailSerializer(test).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description='Y tá hoàn tất quá trình xét nghiệm (Chuyển trạng thái sang COMPLETED)',
        request_body=no_body,
        responses={status.HTTP_200_OK: TestOrderDetailSerializer()}
    )
    @action(methods=['patch'], detail=True, url_path='complete')
    def complete_test(self, request, pk):
        test = self.get_object()

        serializer = self.get_serializer(test, data=request.data)
        serializer.is_valid(raise_exception=True)
        test = serializer.save()

        return Response(TestOrderDetailSerializer(test).data, status=status.HTTP_200_OK)
