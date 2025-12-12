from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from google.oauth2 import id_token
from rest_framework import serializers
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, Role, PatientProfile, DoctorProfile, StaffProfile
from google.auth.transport import requests as google_requests
from cloudinary.uploader import upload


class ProfileSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='user.id', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    phone_number = serializers.CharField(source='user.phone_number')
    address = serializers.CharField(source='user.address')
    gender = serializers.CharField(source='user.gender')
    avatar = serializers.ImageField(source='user.avatar')
    date_of_birth = serializers.DateField(source='user.date_of_birth')

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})

        if user_data:
            user = instance.user

            for k, v in user_data.items():
                setattr(user, k, v)

            user.save()

        return super().update(instance, validated_data)


class PatientProfileSerializer(ProfileSerializer):
    class Meta:
        model = PatientProfile
        fields = ['id', 'email', 'first_name', 'last_name', 'avatar',
                  'phone_number', 'gender', 'address', 'weight', 'height',
                  'blood_type', 'allergies', 'medical_history']
        read_only_fields = ['email', 'id']


class DoctorProfileSerializer(ProfileSerializer):
    class Meta:
        model = DoctorProfile
        fields = ['id', 'email', 'first_name', 'last_name', 'avatar',
                  'phone_number', 'gender', 'address', 'specialty', 'experience_years',
                  'license_number', 'bio', 'consultation_fee']
        read_only_fields = ['email', 'id']


class StaffProfileSerializer(ProfileSerializer):
    class Meta:
        model = StaffProfile
        fields = ['id', 'email', 'first_name', 'last_name', 'avatar',
                  'phone_number', 'gender', 'address']
        read_only_fields = ['email', 'id']


class GoogleAuthSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)

    access_token = serializers.CharField(read_only=True)
    expires_in = serializers.IntegerField(read_only=True)
    token_type = serializers.CharField(read_only=True)
    scope = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)

    def validate(self, attrs):
        token = attrs.get('token')

        try:
            id_info = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
                clock_skew_in_seconds=10
            )

        except ValueError:
            raise serializers.ValidationError({'token': 'Token Google không hợp lệ hoặc đã hết hạn.'})

        email = id_info['email']
        first_name = id_info.get('given_name', '')
        last_name = id_info.get('family_name', '')
        avatar_url = id_info.get('picture', '')

        user = User.objects.filter(email=email).first()

        if user:
            if user.role != Role.PATIENT:
                raise serializers.ValidationError({"error": "Tài khoản Nhân viên vui lòng đăng nhập bằng mật khẩu."})
        else:
            def upload_avatar(url):
                try:
                    result = upload(url, folder='clinic-management/avatars', overwrite=True, resource_type="image")

                    return result['secure_url']

                except Exception:
                    return None

            user = User.objects.create_user(
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=Role.PATIENT,
                password=None,
                avatar=upload_avatar(avatar_url)
            )

        refresh = RefreshToken.for_user(user)

        return {
            'access_token': str(refresh.access_token),
            'expires_in': int(api_settings.ACCESS_TOKEN_LIFETIME.total_seconds()),
            'token_type': 'Bearer',
            "scope": "read write",
            'refresh_token': str(refresh)
        }


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'avatar',
                  'phone_number', 'gender', 'address', 'date_of_birth']
        read_only_fields = ['id', 'email']

    def to_representation(self, instance):
        data = super().to_representation(instance)

        data['avatar'] = instance.avatar.url if instance.avatar else ''

        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password', 'avatar']

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(user.password)
        user.role = Role.PATIENT
        user.save()

        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Mật khẩu cũ không chính xác.")
        return value

    def update(self, instance, validated_data):
        instance.set_password(validated_data['new_password'])
        instance.save()
        return instance


class ResetPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email không tồn tại.")
        return value


class ResetPasswordConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True, write_only=True)
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)

    def validate(self, attrs):
        try:
            uid = force_str(urlsafe_base64_decode(attrs['uid']))
            user = User.objects.get(pk=uid)

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({"token": "Link xác thực không hợp lệ."})

        if not default_token_generator.check_token(user, attrs['token']):
            raise serializers.ValidationError({"token": "Link xác thực không hợp lệ hoặc đã hết hạn."})

        attrs['user'] = user

        return attrs

    def save(self, **kwargs):
        user = self.validated_data['user']
        user.set_password(self.validated_data['new_password'])
        user.save()

        return user