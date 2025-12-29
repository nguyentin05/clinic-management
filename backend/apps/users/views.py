from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from rest_framework import viewsets, permissions, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User, PatientProfile
from .perms import IsDoctorOrPatientOwner
from .serializers import UserSerializer, GoogleAuthSerializer, UserDetailSerializer, UserUpdateSerializer, \
    PatientProfileSerializer, ChangePasswordSerializer, ResetPasswordRequestSerializer, VerifyOTPSerializer, \
    ResetPasswordSerializer


class UserView(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.request.method == 'get' or self.request.method == 'patch':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    @action(methods=['get', 'patch'], url_path='current-user', detail=False)
    def get_current_user(self, request):
        user = request.user

        if request.method == 'patch':
            serializer = UserUpdateSerializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    @action(methods=['get'], url_path='current-user/profile', detail=False)
    def get_current_user_profile(self, request):
        user = request.user

        return Response(UserDetailSerializer(user).data, status=status.HTTP_200_OK)

    @action(methods=['patch'], url_path='change-password', detail=False)
    def change_password(self, request):
        user = request.user

        serializer = ChangePasswordSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"message": "Đổi mật khẩu thành công!"}, status=status.HTTP_200_OK)


class PatientProfileView(viewsets.ViewSet, generics.RetrieveUpdateAPIView):
    queryset = PatientProfile.objects.all()
    serializer_class = PatientProfileSerializer
    permission_classes = [IsDoctorOrPatientOwner]


class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # lay du lieu token y chang oauth2 tra ve
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResetPasswordRequestView(APIView):
    permission_classes = [permissions.AllowAny]

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
    permission_classes = [permissions.AllowAny]

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
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        token = serializer.validated_data['token']
        cache.delete(f"reset_token:{token}")

        return Response({"message": "Đặt lại mật khẩu thành công."}, status=status.HTTP_200_OK)
