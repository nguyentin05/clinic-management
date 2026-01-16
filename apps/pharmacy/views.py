from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.pharmacy.models import Medicine, Prescription, ImportReceipt
from apps.pharmacy.serializers import MedicineSerializer, MedicineDetailSerializer, PrescriptionSerializer, \
    DispenseSerializer, ImportReceiptSerializer, ImportReceiptDetailSerializer, ChangeReceiptSerializer
from apps.pharmacy import paginators
from apps.pharmacy.ultis import param_q, param_cate_id, detail_response_schema, param_date, param_import_status
from apps.users.perms import IsDoctorOrPharmacist, IsPharmacist


class MedicineView(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView):
    queryset = Medicine.objects.filter(active=True)
    pagination_class = paginators.MedicinePaginator
    permission_classes = [IsDoctorOrPharmacist]

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

    @swagger_auto_schema(
        manual_parameters=[param_q, param_cate_id],
        operation_description="Lấy danh sách thuốc (Hỗ trợ tìm kiếm và lọc theo danh mục)"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Xem chi tiết thông tin thuốc",
        responses={200: MedicineDetailSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class PrescriptionView(viewsets.ViewSet, generics.RetrieveAPIView):
    queryset = Prescription.objects.filter(active=True)
    permission_classes = [IsPharmacist]

    def get_serializer_class(self):
        if self.action == 'dispense':
            return DispenseSerializer
        return PrescriptionSerializer

    @swagger_auto_schema(
        operation_description="Xem chi tiết đơn thuốc cần cấp phát",
        responses={200: PrescriptionSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        method='post',
        operation_description='Dược sĩ xác nhận cấp phát thuốc (Hoàn tất đơn thuốc)',
        request_body=no_body,
        responses={200: detail_response_schema}
    )
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
    permission_classes = [IsPharmacist]

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
        manual_parameters=[param_date, param_import_status],
        operation_description="Lấy danh sách phiếu nhập kho (Lọc theo ngày và trạng thái)"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Tạo phiếu nhập kho mới (Draft)",
        responses={201: ImportReceiptDetailSerializer()}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Xem chi tiết phiếu nhập kho",
        responses={200: ImportReceiptDetailSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Cập nhật thông tin phiếu nhập (Khi còn ở trạng thái Draft)",
        responses={200: ImportReceiptDetailSerializer()}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Cập nhật một phần phiếu nhập",
        responses={200: ImportReceiptDetailSerializer()}
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        method='patch',
        operation_description='Chốt phiếu nhập kho (Commit) - Cộng số lượng vào kho thuốc',
        request_body=no_body,
        responses={200: detail_response_schema}
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
        responses={200: detail_response_schema}
    )
    @action(methods=['patch'], detail=True, url_path='cancel')
    def cancel(self, request, pk=None):
        receipt = self.get_object()
        serializer = self.get_serializer(receipt, data=request.data, context={'receipt': receipt, 'action': 'cancel'})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"detail": "Hoàn tất hủy phiếu nhập kho"}, status=status.HTTP_200_OK)
