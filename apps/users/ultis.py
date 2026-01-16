from drf_yasg import openapi

message_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'message': openapi.Schema(type=openapi.TYPE_STRING, description='Thông báo thành công')
    }
)

verify_otp_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'message': openapi.Schema(type=openapi.TYPE_STRING, example='Mã OTP hợp lệ'),
        'temp_token': openapi.Schema(type=openapi.TYPE_STRING,
                                     description='Token tạm thời dùng để reset password (gửi kèm vào API reset-password)')
    }
)

google_login_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'access_token': openapi.Schema(type=openapi.TYPE_STRING, description='Token dùng để gọi API'),
        'refresh_token': openapi.Schema(type=openapi.TYPE_STRING, description='Token dùng để cấp lại access_token'),
        'expires_in': openapi.Schema(type=openapi.TYPE_INTEGER, description='Thời gian hết hạn (giây)'),
        'token_type': openapi.Schema(type=openapi.TYPE_STRING, example='Bearer'),
        'scope': openapi.Schema(type=openapi.TYPE_STRING, description='Phạm vi truy cập'),
    }
)
