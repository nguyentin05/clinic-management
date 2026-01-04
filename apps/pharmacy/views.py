from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.pharmacy.models import Medicine, Prescription, ImportReceipt
from apps.pharmacy.serializers import MedicineSerializer, MedicineDetailSerializer, PrescriptionSerializer, \
    DispenseSerializer, ImportReceiptSerializer, ImportReceiptDetailSerializer, ChangeReceiptSerializer
from apps.pharmacy import paginators


class MedicineView(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView):
    queryset = Medicine.objects.filter(active=True)
    pagination_class = paginators.MedicinePaginator

    def get_serializer_class(self):
        if self.action == 'list':
            return MedicineSerializer
        return MedicineDetailSerializer

    def get_queryset(self):
        query = self.queryset

        q = self.request.query_params.get('q')
        if q:
            query = query.filter(name__icontains=q)

        cate_id = self.request.query_params.get('category_id')
        if cate_id:
            query = query.filter(category_id=cate_id)

        return query


class PrescriptionView(viewsets.ViewSet, generics.RetrieveAPIView):
    queryset = Prescription.objects.filter(active=True)

    def get_serializer_class(self):
        if self.action == 'dispense':
            return DispenseSerializer
        return PrescriptionSerializer

    @swagger_auto_schema(method='post', operation_description='Hoàn tất đơn thuốc',
                         request_body=no_body, responses={200: "Đã hoàn tất đơn thuốc."})
    @action(methods=['post'], detail=True, url_path='dispense')
    def dispense(self, request, pk):
        prescription = self.get_object()

        serializer = self.get_serializer(data=request.data, context={'request': request, 'prescription': prescription})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"detail": "Đã hoàn tất đơn thuốc."}, status=status.HTTP_200_OK)


class ImportReceiptView(viewsets.ViewSet, generics.RetrieveUpdateAPIView, generics.ListCreateAPIView):
    queryset = ImportReceipt.objects.filter(active=True).order_by('-created_date')
    serializer_class = ImportReceiptSerializer

    def get_queryset(self):
        query = self.queryset

        date = self.request.query_params.get('date')
        if date:
            query = query.filter(date__date=date)

        status = self.request.query_params.get('status')
        if status:
            query = query.filter(status=status)

        return query

    def get_serializer_class(self):
        if self.action == 'list':
            return ImportReceiptSerializer
        if self.action == 'commit' or self.action == 'cancel':
            return ChangeReceiptSerializer
        return ImportReceiptDetailSerializer

    @swagger_auto_schema(
        method='patch',
        operation_description='Nộp phiếu nhập kho',
        request_body=no_body,
        responses={200: "Hoàn tất nộp phiếu nhập kho"}
    )
    @action(methods=['patch'], detail=True, url_path='commit')
    def commit(self, request, pk=None):
        receipt = self.get_object()
        serializer = self.get_serializer(receipt, data=request.data, context={'receipt': receipt, 'action': 'commit'})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"detail": "Hoàn tất nộp phiếu nhập kho"}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='patch',
        operation_description='Hủy phiếu nhập kho',
        request_body=no_body,
        responses={200: "Hoàn tất hủy phiếu nhập kho"}
    )
    @action(methods=['patch'], detail=True, url_path='cancel')
    def cancel(self, request, pk=None):
        receipt = self.get_object()
        serializer = self.get_serializer(receipt, data=request.data, context={'receipt': receipt, 'action': 'cancel'})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"detail": "Hoàn tất hủy phiếu nhập kho"}, status=status.HTTP_200_OK)
