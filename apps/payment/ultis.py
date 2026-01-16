import hashlib
import hmac
import urllib.parse
from drf_yasg import openapi


class vnpay:
    def __init__(self):
        self.request_data = {}
        self.response_data = {}

    def get_payment_url(self, vnpay_payment_url, secret_key):
        input_data = sorted(self.request_data.items())
        query_string = ''
        seq = 0
        for key, val in input_data:
            if seq == 1:
                query_string = query_string + "&" + key + '=' + urllib.parse.quote_plus(str(val))
            else:
                seq = 1
                query_string = key + '=' + urllib.parse.quote_plus(str(val))

        hash_value = self.__hmacsha512(secret_key, query_string)
        return vnpay_payment_url + "?" + query_string + '&vnp_SecureHash=' + hash_value

    def validate_response(self, secret_key):
        data_clone = self.response_data.copy()

        vnp_SecureHash = data_clone.get('vnp_SecureHash')

        if 'vnp_SecureHash' in data_clone:
            data_clone.pop('vnp_SecureHash')

        if 'vnp_SecureHashType' in data_clone:
            data_clone.pop('vnp_SecureHashType')

        input_data = sorted(data_clone.items())
        has_data = ''
        seq = 0
        for key, val in input_data:
            if str(key).startswith('vnp_'):
                if seq == 1:
                    has_data = has_data + "&" + str(key) + '=' + urllib.parse.quote_plus(str(val))
                else:
                    seq = 1
                    has_data = str(key) + '=' + urllib.parse.quote_plus(str(val))

        hash_value = self.__hmacsha512(secret_key, has_data)

        return vnp_SecureHash == hash_value

    @staticmethod
    def __hmacsha512(key, data):
        byteKey = key.encode('utf-8')
        byteData = data.encode('utf-8')
        return hmac.new(byteKey, byteData, hashlib.sha512).hexdigest()


param_is_paid = openapi.Parameter(
    'is_paid',
    openapi.IN_QUERY,
    description="Lọc trạng thái thanh toán (true/false)",
    type=openapi.TYPE_BOOLEAN
)

param_payment_method_filter = openapi.Parameter(
    'method',
    openapi.IN_QUERY,
    description="Lọc theo phương thức (CASH, MOMO, VNPAY, STRIPE...)",
    type=openapi.TYPE_STRING
)

param_callback_method = openapi.Parameter(
    'method',
    openapi.IN_PATH,
    description="Tên cổng thanh toán (momo, vnpay, stripe)",
    type=openapi.TYPE_STRING,
    required=True
)

cash_payment_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'message': openapi.Schema(type=openapi.TYPE_STRING, example='Thanh toán thành công'),
        'payment': openapi.Schema(type=openapi.TYPE_OBJECT, description='Chi tiết hóa đơn (PaymentDetailSerializer)')
    }
)

online_payment_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'message': openapi.Schema(type=openapi.TYPE_STRING, example='Tạo giao dịch thành công'),
        'transaction_id': openapi.Schema(type=openapi.TYPE_STRING, description='Mã giao dịch từ cổng thanh toán'),
        'payment_data': openapi.Schema(type=openapi.TYPE_STRING, description='URL thanh toán hoặc QR Code'),
    }
)
