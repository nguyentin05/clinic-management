import hashlib
import hmac
import requests
import stripe
from abc import ABC, abstractmethod
from django.conf import settings
from django.utils import timezone
import uuid

from apps.payment.models import PaymentMethod
from apps.payment.ultis import vnpay


class PaymentStrategy(ABC):
    @abstractmethod
    def process(self, payment, **kwargs):
        pass

    @abstractmethod
    def verify(self, payment, transaction_data):
        pass


class CashPaymentStrategy(PaymentStrategy):
    def process(self, payment, **kwargs):
        try:
            nurse = kwargs.get('nurse')

            if not nurse:
                return {
                    'success': False,
                    'transaction_id': None,
                    'message': 'Thiếu thông tin y tá thu tiền'
                }

            payment.is_paid = True
            payment.paid_date = timezone.now()
            payment.method = PaymentMethod.CASH
            payment.nurse = nurse
            payment.save()

            return {
                'success': True,
                'transaction_id': f"CASH_{payment.id}",
                'message': 'Thanh toán tiền mặt thành công',
                'data': {
                    'amount': str(payment.amount),
                    'nurse': nurse.get_full_name()
                }
            }

        except Exception as e:
            return {
                'success': False,
                'transaction_id': None,
                'message': f'Lỗi xử lý thanh toán: {str(e)}'
            }

    def verify(self, payment, transaction_data):
        return payment.is_paid


# momo là redirect
class MoMoPaymentStrategy(PaymentStrategy):
    def __init__(self):
        self.partner_code = settings.MOMO_PARTNER_CODE
        self.access_key = settings.MOMO_ACCESS_KEY
        self.secret_key = settings.MOMO_SECRET_KEY
        self.endpoint = settings.MOMO_ENDPOINT
        self.ipn_url = settings.MOMO_IPN_URL

    def process(self, payment, **kwargs):
        timestamp = int(timezone.now().timestamp())
        order_id = f"{payment.id}_{timestamp}"
        request_id = str(uuid.uuid4())
        extra_data = ''
        order_info = ''
        redirect_url = kwargs.get('redirect_url')
        if payment.appointment:
            order_info = "Thanh toán lịch khám"
        elif payment.get_prescription:
            order_info = "Thanh toán đơn thuốc"

        raw_signature = (
            f"accessKey={self.access_key}"
            f"&amount={str(int(payment.amount))}"
            f"&extraData={extra_data}"
            f"&ipnUrl={self.ipn_url}"
            f"&orderId={order_id}"
            f"&orderInfo={order_info}"
            f"&partnerCode={self.partner_code}"
            f"&redirectUrl={redirect_url}"
            f"&requestId={request_id}"
            f"&requestType=captureWallet"
        )

        signature = hmac.new(self.secret_key.encode('utf-8'), raw_signature.encode('utf-8'),
                             hashlib.sha256).hexdigest()

        payload = {
            "partnerCode": self.partner_code,
            "partnerName": "CLINICNITT",
            "storeId": "ClinicManagement",
            "requestId": request_id,
            "amount": str(int(payment.amount)),
            "orderId": order_id,
            "orderInfo": order_info,
            "redirectUrl": redirect_url,
            "ipnUrl": self.ipn_url,
            "lang": "vi",
            "extraData": extra_data,
            "requestType": 'captureWallet',
            "signature": signature,
        }

        try:
            response = requests.post(self.endpoint, json=payload, timeout=30)

            res_json = response.json()

            if res_json.get("resultCode") == 0:
                return {
                    'success': True,
                    'transaction_id': request_id,
                    'message': 'Tạo thanh toán MoMo thành công',
                    'data': {
                        'pay_url': res_json.get('payUrl'),
                        'qr_code_url': res_json.get('qrCodeUrl'),
                        'deep_link': res_json.get('deeplink'),
                        'order_id': order_id
                    }
                }
            else:
                return {
                    'success': False,
                    'transaction_id': None,
                    'message': f"MoMo error: {res_json.get('message')}"
                }

        except Exception as e:
            return {
                'success': False,
                'transaction_id': None,
                'message': f'Lỗi kết nối MoMo: {str(e)}'
            }

    def verify(self, payment, transaction_data):
        try:
            # lấy chữ ký đã gửi
            signature = transaction_data.get('signature')

            raw_signature = (
                f"accessKey={self.access_key}"
                f"&amount={transaction_data.get('amount')}"
                f"&extraData={transaction_data.get('extraData')}"
                f"&message={transaction_data.get('message')}"
                f"&orderId={transaction_data.get('orderId')}"
                f"&orderInfo={transaction_data.get('orderInfo')}"
                f"&orderType={transaction_data.get('orderType')}"
                f"&partnerCode={transaction_data.get('partnerCode')}"
                f"&payType={transaction_data.get('payType')}"
                f"&requestId={transaction_data.get('requestId')}"
                f"&responseTime={transaction_data.get('responseTime')}"
                f"&resultCode={transaction_data.get('resultCode')}"
                f"&transId={transaction_data.get('transId')}"
            )

            tmp_signature = hmac.new(self.secret_key.encode('utf-8'), raw_signature.encode('utf-8'),
                                     hashlib.sha256).hexdigest()

            # xác thực với chữ ký của momo đã tạo
            return signature == tmp_signature

        except Exception as e:
            print(str(e))
            return False


# stripe là embedded
class StripePaymentStrategy(PaymentStrategy):
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.publishable_key = settings.STRIPE_PUBLISHABLE_KEY

    def process(self, payment, **kwargs):
        try:
            description = ''
            if payment.appointment:
                description = "Thanh toán lịch khám"
            elif payment.get_prescription:
                description = "Thanh toán đơn thuốc"

            # tạo 1 giao dịch chờ
            intent = stripe.PaymentIntent.create(
                amount=int(payment.amount),
                currency='vnd',
                description=description,
                metadata={
                    'payment_id': payment.id,
                    'patient_id': payment.patient.id
                },
                automatic_payment_methods={'enabled': True}
            )

            return {
                'success': True,
                'transaction_id': intent.id,
                'message': 'Tạo thanh toán Stripe thành công',
                'data': {
                    'client_secret': intent.client_secret,
                    'publishable_key': self.publishable_key,
                    'payment_intent_id': intent.id
                }
            }

        except stripe.error.StripeError as e:
            return {
                'success': False,
                'transaction_id': None,
                'message': f'Stripe error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'transaction_id': None,
                'message': f'Lỗi xử lý thanh toán: {str(e)}'
            }

    def verify(self, payment, transaction_data):
        try:
            sign = transaction_data.get('stripe_signature')
            payload = transaction_data.get('payload')

            # webhook tự động verify của stripe
            event = stripe.Webhook.construct_event(payload, sign, settings.STRIPE_WEBHOOK_SECRET)

            return event.type == 'payment_intent.succeeded'

        except Exception as e:
            print(str(e))
            return False

class VNPayPaymentStrategy(PaymentStrategy):
    def __init__(self):
        self.tmn_code = settings.VNPAY_TMN_CODE
        self.hash_secret = settings.VNPAY_HASH_SECRET_KEY
        self.payment_url = settings.VNPAY_PAYMENT_URL

    def process(self, payment, **kwargs):
        try:
            order_info = ''
            if payment.appointment:
                order_info = "Thanh toán lịch khám"
            elif payment.get_prescription:
                order_info = "Thanh toán đơn thuốc"

            vnp = vnpay()

            vnp.request_data['vnp_Version'] = '2.1.0'
            vnp.request_data['vnp_Command'] = 'pay'
            vnp.request_data['vnp_TmnCode'] = self.tmn_code
            vnp.request_data['vnp_Amount'] = str(int(payment.amount * 100))
            vnp.request_data['vnp_CurrCode'] = 'VND'
            vnp.request_data['vnp_TxnRef'] = payment.code
            vnp.request_data['vnp_OrderInfo'] = order_info
            vnp.request_data['vnp_OrderType'] = 'other'
            vnp.request_data['vnp_Locale'] = 'vn'
            vnp.request_data['vnp_CreateDate'] = timezone.now().strftime('%Y%m%d%H%M%S')
            vnp.request_data['vnp_IpAddr'] = kwargs.get('ip_addr')
            vnp.request_data['vnp_ReturnUrl'] = kwargs.get('redirect_url')

            payment_url = vnp.get_payment_url(self.payment_url, self.hash_secret)

            return {
                'success': True,
                'transaction_id': payment.id,
                'message': 'Tạo thanh toán VNPay thành công',
                'data': {
                    'payment_url': payment_url,
                    'transaction_ref': payment.id
                }
            }

        except Exception as e:
            return {
                'success': False,
                'transaction_id': None,
                'message': f'Lỗi tạo thanh toán VNPay: {str(e)}'
            }

    def verify(self, payment, transaction_data):
        try:
            vnp = vnpay()
            vnp.response_data = transaction_data

            return vnp.validate_response(self.hash_secret)

        except Exception as e:
            print(str(e))
            return False


class PaymentStrategyFactory:
    _strategies = {
        'CASH': CashPaymentStrategy,
        'MOMO': MoMoPaymentStrategy,
        'STRIPE': StripePaymentStrategy,
        'VNPAY': VNPayPaymentStrategy,
    }

    @classmethod
    def get_strategy(cls, method):
        strategy_class = cls._strategies.get(method)

        return strategy_class()
