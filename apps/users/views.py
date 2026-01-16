from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User, PatientProfile, UserRole, EmployeeRole
from .serializers import UserSerializer, GoogleAuthSerializer, UserDetailSerializer, UserUpdateSerializer, \
    PatientProfileSerializer, ChangePasswordSerializer, ResetPasswordRequestSerializer, VerifyOTPSerializer, \
    ResetPasswordSerializer, UpdateFCMSerializer, DoctorInfoSerializer
from .ultis import message_response, google_login_response, verify_otp_response


class UserView(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'change_password':
            return ChangePasswordSerializer
        if self.action == 'fcm_update':
            return UpdateFCMSerializer
        if self.action == 'get_current_user':
            return UserUpdateSerializer
        return UserSerializer

    @swagger_auto_schema(
        operation_description="Đăng ký tài khoản người dùng mới (Bệnh nhân)",
        responses={201: UserSerializer()}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        methods=['get'],
        operation_description="Lấy thông tin cơ bản của user đang đăng nhập",
        responses={200: UserSerializer()}
    )
    @swagger_auto_schema(
        methods=['patch'],
        operation_description="Cập nhật thông tin cơ bản (Họ tên, SĐT, Avatar...)",
        request_body=UserUpdateSerializer,
        responses={200: UserSerializer()}
    )
    @action(methods=['get', 'patch'], url_path='current-user', detail=False)
    def get_current_user(self, request):
        user = request.user

        if request.method == 'patch':
            serializer = self.get_serializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Lấy hồ sơ đầy đủ của User (Bao gồm cả thông tin Bệnh nhân/Bác sĩ/Nhân viên)",
        responses={200: UserDetailSerializer()}
    )
    @action(methods=['get'], url_path='current-user/profile', detail=False)
    def get_current_user_profile(self, request):
        user = request.user

        return Response(UserDetailSerializer(user).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Đổi mật khẩu",
        request_body=ChangePasswordSerializer,
        responses={200: message_response}
    )
    @action(methods=['patch'], url_path='change-password', detail=False)
    def change_password(self, request):
        user = request.user

        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"message": "Đổi mật khẩu thành công!"}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Cập nhật FCM Token (Dùng cho bắn thông báo đẩy)",
        request_body=UpdateFCMSerializer,
        responses={200: message_response}
    )
    @action(methods=['patch'], url_path='fcm-update', detail=False)
    def fcm_update(self, request):
        user = request.user

        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"message": "Cập nhật fcm thành công!"}, status=status.HTTP_200_OK)


class PatientProfileView(viewsets.ViewSet, generics.RetrieveUpdateAPIView):
    queryset = PatientProfile.objects.all()
    serializer_class = PatientProfileSerializer

    @swagger_auto_schema(
        operation_description="Xem chi tiết hồ sơ bệnh nhân (Tiền sử bệnh, dị ứng...)",
        responses={200: PatientProfileSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Cập nhật hồ sơ bệnh nhân",
        request_body=PatientProfileSerializer,
        responses={200: PatientProfileSerializer()}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Cập nhật một phần hồ sơ bệnh nhân",
        request_body=PatientProfileSerializer,
        responses={200: PatientProfileSerializer()}
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Đăng nhập bằng Google Access Token",
        request_body=GoogleAuthSerializer,
        responses={200: google_login_response}
    )
    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # lay du lieu token y chang oauth2 tra ve
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResetPasswordRequestView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Bước 1: Yêu cầu đặt lại mật khẩu (Gửi email chứa OTP)",
        request_body=ResetPasswordRequestSerializer,
        responses={200: message_response}
    )
    def post(self, request):
        serializer = ResetPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        #
        # cache_key = f"password_reset_request:{email}"

        # Check rate limiting with Redis
        # attempts = cache.get(cache_key, 0)
        #
        # if attempts >= 3:
        #     return Response(
        #         {"error": "Đã yêu cầu quá nhiều lần"},
        #         status=status.HTTP_429_TOO_MANY_REQUESTS
        #     )

        # Create OTP
        # otp = PasswordResetOTP.create_otp(email)

        otp = get_random_string(length=6, allowed_chars='0123456789')

        user = User.objects.get(email=email)

        subject = "Ma Xac Thuc Dat Lai MK - Clinic Management"
        message = f"""
        Hi {user.first_name},

        Ma xac thuc de dat lai mk cua ban la:

        {otp}

        Ma nay co hieu luc trong {settings.OTP_EXPIRY_MINUTES} phut.

        Tran trong,
        Clinic Management System
        """

        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False
            )

            otp_cache_key = f"password_reset_otp:{email}"
            cache.set(otp_cache_key, otp, timeout=settings.OTP_EXPIRY_MINUTES * 60)

            return Response(
                {"message": "Mã OTP đã được gửi đến email của bạn."},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            print(f"Email sending error: {str(e)}")
            return Response(
                {"error": "Không thể gửi email."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Bước 2: Xác thực mã OTP đã nhận trong email. Trả về temp_token để dùng cho bước 3.",
        request_body=VerifyOTPSerializer,
        responses={200: verify_otp_response}
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        temp_token = get_random_string(length=32)

        cache.set(f"reset_token:{temp_token}", email, timeout=300)

        cache.delete(f"password_reset_otp:{email}")

        # Increase attempt count
        # otp = serializer.validated_data['otp_instance']
        # otp.attempts += 1
        # otp.save()

        return Response(
            {
                "message": "Mã OTP hợp lệ",
                "temp_token": temp_token
            }, status=status.HTTP_200_OK
        )


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Bước 3: Đặt lại mật khẩu mới (Cần temp_token từ Bước 2)",
        request_body=ResetPasswordSerializer,
        responses={200: message_response}
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        token = serializer.validated_data['token']
        cache.delete(f"reset_token:{token}")

        return Response({"message": "Đặt lại mật khẩu thành công."}, status=status.HTTP_200_OK)


class DoctorBookingView(viewsets.ViewSet, generics.ListAPIView):
    serializer_class = DoctorInfoSerializer

    queryset = User.objects.select_related('doctor_profile', 'doctor_profile__specialty').filter(
        user_role=UserRole.EMPLOYEE,
        employee_role=EmployeeRole.DOCTOR,
        is_active=True
    ).order_by('-doctor_profile__rating')

    @swagger_auto_schema(
        operation_description="Lấy danh sách bác sĩ (Sắp xếp theo đánh giá từ cao xuống thấp)",
        responses={200: DoctorInfoSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
