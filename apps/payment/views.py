from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema, no_body
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.payment.models import Payment, PaymentMethod
from apps.payment.perms import IsOwnerPayment, IsOwnerOnlinePayment
from apps.payment.serializers import PaymentSerializer, OnlinePaymentSerializer, PaymentStatusSerializer, \
    PaymentDetailSerializer
from apps.payment.strategies import PaymentStrategyFactory
from apps.payment.ultis import param_is_paid, param_payment_method_filter, cash_payment_response, \
    online_payment_response, param_callback_method
from apps.users.models import UserRole
from apps.users.perms import IsNurse




class PaymentViewSet(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView):
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsOwnerPayment(), IsAuthenticated()]
        if self.action == 'cash_payment':
            return [IsNurse()]
        if self.action == 'callback':
            return [AllowAny()]
        if self.action in ['check_status', 'online_payment']:
            return [IsOwnerOnlinePayment(), IsAuthenticated()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        query = Payment.objects.select_related('patient', 'appointment', 'prescription', 'nurse').filter(active=True)

        if user.is_authenticated and hasattr(user, 'user_role'):
            if user.user_role == UserRole.PATIENT:
                query = query.filter(patient=user)
            elif user.user_role == UserRole.EMPLOYEE:
                query = query.filter(nurse=user)

        is_paid = self.request.query_params.get('is_paid')
        if is_paid:
            is_paid_bool = is_paid.lower() == 'true'
            query = query.filter(is_paid=is_paid_bool)

        method = self.request.query_params.get('method')
        if method:
            query = query.filter(method=method)

        return query.order_by('-created_date')

    def get_serializer_class(self):
        if self.action == 'list':
            return PaymentSerializer
        return PaymentDetailSerializer

    @swagger_auto_schema(
        manual_parameters=[param_is_paid, param_payment_method_filter],
        operation_description="Lấy danh sách lịch sử thanh toán (Có thể lọc theo trạng thái và phương thức)"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Xem chi tiết một hóa đơn thanh toán",
        responses={200: PaymentDetailSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description='Xác nhận thanh toán bằng tiền mặt (Dành cho Y tá/Thu ngân)',
        request_body=no_body,
        responses={
            status.HTTP_200_OK: cash_payment_response,
            status.HTTP_400_BAD_REQUEST: "Hóa đơn đã được thanh toán hoặc lỗi xử lý"
        }
    )
    @action(methods=['post'], detail=True, url_path='cash')
    def cash_payment(self, request, pk):
        payment = get_object_or_404(Payment, id=pk, active=True)

        if payment.is_paid:
            return Response({"error": "Hóa đơn này đã được thanh toán trước đó."}, status=status.HTTP_400_BAD_REQUEST)

        strategy = PaymentStrategyFactory.get_strategy(PaymentMethod.CASH)

        result = strategy.process(payment, nurse=request.user)

        if result['success']:
            payment.refresh_from_db()

            return Response({
                "message": result['message'],
                "payment": PaymentDetailSerializer(payment).data
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": result['message']}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description='Tạo yêu cầu thanh toán Online (Momo, VNPay, Stripe).\nTrả về URL để redirect user sang trang thanh toán.',
        request_body=OnlinePaymentSerializer,
        responses={
            status.HTTP_200_OK: online_payment_response,
            status.HTTP_400_BAD_REQUEST: "Lỗi tạo giao dịch"
        }
    )
    @action(methods=['post'], detail=True, url_path='online')
    def online_payment(self, request, pk):
        serializer = OnlinePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment = get_object_or_404(Payment, id=pk, active=True)
        payment_method = serializer.validated_data['payment_method']

        # Get client IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_addr = x_forwarded_for.split(',')[0]
        else:
            ip_addr = request.META.get('REMOTE_ADDR')

        try:
            strategy = PaymentStrategyFactory.get_strategy(payment_method)

            result = strategy.process(payment, ip_addr=ip_addr,
                                      redirect_url=serializer.validated_data.get('redirect_url'))

            if result['success']:
                payment.method = payment_method
                payment.save(update_fields=['method'])

                return Response({
                    "message": result['message'],
                    "transaction_id": result['transaction_id'],
                    "payment_data": result['data']
                }, status=status.HTTP_200_OK)
            else:
                return Response({"error": result['message']}, status=status.HTTP_400_BAD_REQUEST)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        manual_parameters=[param_callback_method],
        operation_description='Webhook nhận kết quả thanh toán từ bên thứ 3 (Momo/VNPay/Stripe). \nAPI này được gọi tự động bởi cổng thanh toán, Client không gọi trực tiếp.',
        responses={
            status.HTTP_200_OK: "Payment success",
            status.HTTP_400_BAD_REQUEST: "Invalid signature / Payment failed"
        }
    )
    @action(methods=['post'], detail=False, url_path='callback/(?P<method>[^/.]+)')
    def callback(self, request, method):
        try:
            strategy = PaymentStrategyFactory.get_strategy(method.upper())

            if method == 'stripe':
                transaction_data = {
                    'payload': request.body,
                    'stripe_signature': request.headers.get('Stripe-Signature'),
                    'data': request.data
                }
            elif method == 'vnpay':
                transaction_data = request.query_params.dict()
            else:
                transaction_data = request.data

            if method == 'momo':
                id = transaction_data.get('orderId').split('_')[0]
                is_success = transaction_data.get('resultCode') == 0
                transaction_id = transaction_data.get('transId')
            elif method == 'stripe':
                data_object = transaction_data.get('data', {}).get('object', {})

                id = data_object.get('metadata', {}).get('payment_id')
                is_success = transaction_data.get('type') == 'payment_intent.succeeded'
                transaction_id = data_object.get('id')
            else:
                id = transaction_data.get('vnp_TxnRef')
                is_success = transaction_data.get('vnp_ResponseCode') == '00'
                transaction_id = transaction_data.get('vnp_TransactionNo')

            if not id:
                return Response({"error": "Không tìm thấy Payment ID"}, status=status.HTTP_400_BAD_REQUEST)

            payment = get_object_or_404(Payment, id=id, active=True)

            if not strategy.verify(payment, transaction_data):
                return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

            if is_success:
                payment.is_paid = True
                payment.paid_date = timezone.now()
                payment.transaction_id = transaction_id
                payment.save()

                return Response({"message": "Payment success"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Payment failed"}, status=status.HTTP_400_BAD_REQUEST)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_description='Kiểm tra trạng thái hiện tại của hóa đơn',
        responses={200: PaymentStatusSerializer()}
    )
    @action(methods=['get'], detail=True, url_path='check-status')
    def check_status(self, request, pk):
        payment = get_object_or_404(Payment, id=pk, active=True)

        return Response(PaymentStatusSerializer(payment, data=request.data).data, status=status.HTTP_200_OK)