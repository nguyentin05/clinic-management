from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import viewsets, permissions, generics, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User, Role
from .serializers import UserSerializer, UserRegistrationSerializer, GoogleAuthSerializer, PatientProfileSerializer, \
    DoctorProfileSerializer, StaffProfileSerializer, ChangePasswordSerializer, ResetPasswordRequestSerializer, \
    ResetPasswordConfirmSerializer


class UserView(viewsets.ViewSet, generics.CreateAPIView):
    parser_classes = [MultiPartParser, JSONParser]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserRegistrationSerializer

        elif self.action == 'change_password':
            return ChangePasswordSerializer

        return UserSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.AllowAny()]

        return [permissions.IsAuthenticated()]

    @action(methods=['get', 'patch'], url_path='current-user', detail=False)
    def get_current_user(self, request):
        user = request.user

        ROLE_MAP = {
            Role.PATIENT: (PatientProfileSerializer, 'patient_profile'),
            Role.DOCTOR: (DoctorProfileSerializer, 'doctor_profile'),
            Role.STAFF: (StaffProfileSerializer, 'staff_profile')
        }

        serializer_class, profile = ROLE_MAP.get(user.role, (UserSerializer, None))

        if profile:
            instance = getattr(user, profile, None)

        else:
            instance = user

        # neu co profile
        if instance:
            if request.method == 'GET':
                return Response(serializer_class(instance).data, status=status.HTTP_200_OK)

            if request.method == 'PATCH':
                serializer = serializer_class(instance, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()

                return Response(serializer.data, status=status.HTTP_200_OK)

        return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(methods=['patch'], url_path='change-password', detail=False)
    def change_password(self, request):
        user = request.user

        serializer = ChangePasswordSerializer(user, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"message": "Đổi mật khẩu thành công!"}, status=status.HTTP_200_OK)


class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class ResetPasswordRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResetPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        user = User.objects.get(email=email)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        reset_link = f"{settings.FRONTEND_URL}?uid={uid}&token={token}"

        subject = "Reset Password - Clinic App"
        message = f"HI {user.first_name},\n\nClick here:\n\n{reset_link}\n\n"

        try:
            send_mail(subject, message, settings.EMAIL_HOST_USER, [email], fail_silently=False)
            return Response({"message": "Vui lòng kiểm tra email để lấy lại mật khẩu."}, status=status.HTTP_200_OK)

        except Exception as ex:
            print(str(ex))
            return Response({"error": "Lỗi gửi email hệ thống."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResetPasswordConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResetPasswordConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"message": "Mật khẩu đã được đặt lại thành công."}, status=status.HTTP_200_OK)