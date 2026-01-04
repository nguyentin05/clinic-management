from drf_yasg.utils import swagger_auto_schema, no_body
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.medical.models import TestOrder
from apps.medical.perms import IsNurse
from apps.medical.serializers import TestOrderSerializer, ConfirmTestOrderSerializer, TestOrderDetailSerializer, \
    CancelTestOrderSerializer, CompleteTestOrderSerializer


#CHƯA PHÂN QUYỀN
class TestOrderView(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView):
    queryset = TestOrder.objects.filter(active=True)

    def get_permissions(self):
        if self.action == 'list' or self.action == 'confirm_test':
            return [IsNurse()]
        return [IsAuthenticated()]

    def get_queryset(self):
        query = self.queryset.select_related(
            'service', 'service__specialty', 'nurse','medical_record', 'medical_record__appointment',
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

        return TestOrderDetailSerializer

    @swagger_auto_schema(operation_description='Xác nhận xét nghiệm', request_body=no_body,
                         responses={status.HTTP_200_OK: TestOrderDetailSerializer()})
    @action(methods=['patch'], detail=True, url_path='confirm')
    def confirm_test(self, request, pk):
        test = self.get_object()

        serializer = self.get_serializer(test, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        test = serializer.save()

        return Response(TestOrderDetailSerializer(test).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(operation_description='Tùy theo role mà gửi đúng trường nhé, ko là server nó ko nhận đâu:)')
    # cập nhật này dùng cho cả y tá và bác sĩ nhưng phân theo role và trạng thái
    @action(methods=['patch'], detail=True, url_path='update')
    def update_test(self, request, pk):
        test = self.get_object()

        serializer = self.get_serializer(test, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(operation_description='Xác nhận xét nghiệm', request_body=CancelTestOrderSerializer(),
                         responses={status.HTTP_200_OK: TestOrderDetailSerializer()})
    @action(methods=['patch'], detail=True, url_path='cancel')
    def cancel_test(self, request, pk):
        test = self.get_object()

        serializer = self.get_serializer(test, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        test = serializer.save()

        return Response(TestOrderDetailSerializer(test).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(operation_description='Hoàn tất xét nghiệm', request_body=no_body,
                         responses={status.HTTP_200_OK: TestOrderDetailSerializer()})
    @action(methods=['patch'], detail=True, url_path='complete')
    def complete_test(self, request, pk):
        test = self.get_object()

        serializer = self.get_serializer(test, data=request.data)
        serializer.is_valid(raise_exception=True)
        test = serializer.save()

        return Response(TestOrderDetailSerializer(test).data, status=status.HTTP_200_OK)
