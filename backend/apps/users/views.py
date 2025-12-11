from cloudinary.uploader import upload
from django.conf import settings
from google.oauth2 import id_token
from rest_framework import viewsets, permissions, generics, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from google.auth.transport import requests as google_requests

from .models import User, Role
from .serializers import UserSerializer, UserRegistrationSerializer, GoogleAuthSerializer, PatientProfileSerializer, \
    DoctorProfileSerializer, StaffProfileSerializer


class UserView(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)
    parser_classes = [MultiPartParser, JSONParser]

    def get_serializer_class(self):
        if self.request.method.__eq__('POST'):
            return UserRegistrationSerializer
        return UserSerializer

    @action(methods=['get', 'patch'], url_path='current-user', detail=False, permission_classes=[permissions.IsAuthenticated])
    def get_current_user(self, request):
        user = request.user

        ROLE_CONFIG = {
            Role.PATIENT: (PatientProfileSerializer, 'patient_profile'),
            Role.DOCTOR: (DoctorProfileSerializer, 'doctor_profile'),
            Role.STAFF: (StaffProfileSerializer, 'staff_profile')
        }

        serializer_class, profile = ROLE_CONFIG.get(user.role, (UserSerializer, None))

        if profile:
            instance = getattr(user, profile, None)
        else:
            instance = user

        if instance is None:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)

        if request.method.__eq__('GET'):
            return Response(serializer_class(instance).data, status=status.HTTP_200_OK)

        if request.method.__eq__('PATCH'):
            serializer = serializer_class(instance, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        token = serializer.validated_data['token']

        try:
            id_info = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
                clock_skew_in_seconds=10
            )

            email = id_info['email']
            first_name = id_info.get('given_name', '')
            last_name = id_info.get('family_name', '')
            avatar = id_info.get('picture', '')

        except ValueError as ex:
            return Response({'error': 'Token Google không hợp lệ', 'detail': str(ex)},
                            status=status.HTTP_400_BAD_REQUEST)

        def upload_avatar(google_url):
            try:
                result = upload(google_url, folder='clinic-management/avatars', overwrite=True, resource_type="image")

                return result['secure_url']

            except Exception as e:
                print(f"Lỗi upload: {e}")
                return None

        user = User.objects.filter(email=email).first()

        if user:
            if user.role != Role.PATIENT:
                return Response(
                    {'error': 'Tài khoản Nhân viên vui lòng đăng nhập bằng Mật khẩu.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        else:
            user = User.objects.create_user(
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=Role.PATIENT,
                password=None,
                avatar=upload_avatar(avatar)
            )

        token = RefreshToken.for_user(user)

        return Response({
            'access_token': str(token.access_token),
            'expires_in': int(api_settings.ACCESS_TOKEN_LIFETIME.total_seconds()),
            'token_type': 'Bearer',
            "scope": "read write",
            "refresh_token": str(token)
        }, status=status.HTTP_200_OK)