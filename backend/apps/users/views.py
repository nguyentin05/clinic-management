from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from google.oauth2 import id_token
from oauth2_provider.models import Application, AccessToken, RefreshToken
from oauth2_provider.settings import oauth2_settings
from rest_framework import viewsets, permissions, generics, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from google.auth.transport import requests as google_requests

from .models import User, Role
from .serializers import UserSerializer, UserRegistrationSerializer, GoogleAuthSerializer


class UserView(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)
    parser_classes = [MultiPartParser]

    def get_serializer_class(self):
        if self.action.__eq__('create'):
            return UserRegistrationSerializer
        return UserSerializer

    @action(methods=['get', 'patch'], url_path='current-user', detail=False, permission_classes=[permissions.IsAuthenticated])
    def get_current_user(self, request):
        user = request.user
        if request.method.__eq__('PATCH'):
            for k, v in request.data.items():
                if k in ['first_name', 'last_name', 'phone_number', 'address', 'gender', 'date_of_birth', 'avatar']:
                    setattr(user, k, v)
            user.save()

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


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
            # lay anh tu tk google luon
            # avatar_url = id_info.get('picture', '')

        except ValueError as e:
            return Response({'error': 'Token Google không hợp lệ', 'detail': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)

            if user.role != Role.PATIENT:
                return Response(
                    {'error': 'Tài khoản Bác sĩ/Nhân viên vui lòng đăng nhập bằng Mật khẩu.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except User.DoesNotExist:
            user = User.objects.create_user(
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=Role.PATIENT,
                password=None
            )

        app = Application.objects.first()
        if not app:
            return Response({'error': 'Chưa cấu hình OAuth Application trong Admin'}, status=500)

        AccessToken.objects.filter(user=user, application=app, expires__lt=timezone.now()).delete()

        expires = timezone.now() + timedelta(seconds=oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS)
        access_token = AccessToken.objects.create(
            user=user,
            application=app,
            token=f"google_{timezone.now().timestamp()}",
            expires=expires,
            scope='read write'
        )

        RefreshToken.objects.create(
            user=user,
            application=app,
            token=f"refresh_google_{timezone.now().timestamp()}",
            access_token=access_token
        )

        return Response({
            'access_token': access_token.token,
            'expires_in': oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS,
            'token_type': 'Bearer',
            'scope': access_token.scope,
            'user': UserSerializer(user).data
        })