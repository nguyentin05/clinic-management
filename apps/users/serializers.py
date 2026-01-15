import uuid
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string
from google.oauth2 import id_token
from oauth2_provider.models import Application, RefreshToken, AccessToken
from oauth2_provider.settings import oauth2_settings
from rest_framework import serializers

from .models import User, PatientProfile, DoctorProfile, UserRole, EmployeeRole, NurseProfile, PharmacistProfile
from google.auth.transport import requests as google_requests
from cloudinary.uploader import upload


# login gg
class GoogleAuthSerializer(serializers.Serializer):
    token = serializers.CharField(required=True, write_only=True)

    access_token = serializers.CharField(read_only=True)
    expires_in = serializers.IntegerField(read_only=True)
    token_type = serializers.CharField(read_only=True)
    scope = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)

    @transaction.atomic
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
            raise serializers.ValidationError('Token Google không hợp lệ hoặc đã hết hạn.')

        email = id_info['email']
        first_name = id_info.get('given_name', '')
        last_name = id_info.get('family_name', '')
        avatar_url = id_info.get('picture', '')

        user = User.objects.filter(email=email).first()

        if user:
            if user.user_role != UserRole.PATIENT:
                raise serializers.ValidationError("Tài khoản Nhân viên vui lòng đăng nhập bằng mật khẩu.")
        else:
            def upload_avatar(url):
                try:
                    result = upload(url, folder='clinic-management/avatars', overwrite=True, resource_type="image")

                    return result['public_id']

                except Exception as ex:
                    print(ex)
                    return None

            user = User.objects.create_user(
                email=email,
                first_name=first_name,
                last_name=last_name,
                user_role=UserRole.PATIENT,
                password=None,
                avatar=upload_avatar(avatar_url)
            )
            user.set_unusable_password()
            user.save()

        app = Application.objects.first()

        expires = timezone.now() + timedelta(seconds=oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS)

        access_token = AccessToken.objects.create(
            user=user,
            application=app,
            token=get_random_string(30),
            expires=expires,
            scope="read write"
        )

        refresh_token = RefreshToken.objects.create(
            user=user,
            application=app,
            token=get_random_string(30),
            access_token=access_token,
            token_family=str(uuid.uuid4())
        )

        return {
            'access_token': access_token.token,
            'expires_in': oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS,
            'token_type': 'Bearer',
            "scope": access_token.scope,
            'refresh_token': refresh_token.token
        }


# thong tin trong lich hen
class DoctorProfilePublicSerializer(serializers.ModelSerializer):
    specialty_name = serializers.CharField(source='specialty.name', read_only=True)

    class Meta:
        model = DoctorProfile
        fields = ['specialty', 'specialty_name', 'bio', 'consultation_fee',
                  'rating', 'total_reviews', 'total_patients', 'is_available']


# thong tin trong lich hen
class PatientProfilePublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        fields = ['blood_type', 'allergies', 'chronic_diseases',
                  'medical_history', 'height', 'weight']


# thong tin trong lich hen
class BasicInfoSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'full_name', 'avatar']


# thong tin trong lich hen
class DoctorInfoSerializer(BasicInfoSerializer):
    public_profile = DoctorProfilePublicSerializer(source='doctor_profile')

    class Meta:
        model = BasicInfoSerializer.Meta.model
        fields = BasicInfoSerializer.Meta.fields + ['public_profile']


# thong tin trong lich hen
class PatientInfoSerializer(BasicInfoSerializer):
    public_profile = PatientProfilePublicSerializer(source='patient_profile')

    class Meta:
        model = BasicInfoSerializer.Meta.model
        fields = BasicInfoSerializer.Meta.fields + ['public_profile']


class DoctorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorProfile
        fields = '__all__'


class PatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        fields = '__all__'
        read_only_fields = ['patient_code']


class NurseProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = NurseProfile
        fields = '__all__'


class PharmacistProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacistProfile
        fields = '__all__'


# xem thong tin co ban
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'avatar', 'password',
                  'phone', 'gender', 'address', 'date_of_birth', 'user_role', 'employee_id', 'hire_date',
                  'employee_role']
        read_only_fields = ['user_role', 'employee_id', 'hire_date', 'employee_role']
        extra_kwargs = {
            'password': {
                'write_only': True
            }
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.user_role != UserRole.EMPLOYEE:
            for field in ['employee_id', 'employee_role', 'hire_date']:
                data.pop(field, None)

        data['avatar'] = instance.avatar.url if instance.avatar else ''

        return data

    @transaction.atomic
    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(user.password)
        user.user_role = UserRole.PATIENT
        user.save()

        return user


# xem profile chi tiet
class UserDetailSerializer(UserSerializer):
    profile = serializers.SerializerMethodField()

    def get_profile(self, instance):
        if instance.user_role == UserRole.PATIENT:
            return PatientProfileSerializer(instance.patient_profile).data

        elif instance.user_role == UserRole.EMPLOYEE:
            if instance.employee_role == EmployeeRole.DOCTOR:
                return DoctorProfileSerializer(instance.doctor_profile).data
            elif instance.employee_role == EmployeeRole.NURSE:
                return NurseProfileSerializer(instance.nurse_profile).data
            elif instance.employee_role == EmployeeRole.PHARMACIST:
                return PharmacistProfileSerializer(instance.pharmacist_profile).data

        return None

    class Meta:
        model = UserSerializer.Meta.model
        fields = UserSerializer.Meta.fields + ['profile']


# cap nhat thong tin co ban
class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'avatar', 'phone', 'gender', 'address', 'date_of_birth', 'email']
        read_only_fields = ['email']


# doi mat khau
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    # tạm thời ko cần phức tạp
    # new_password = serializers.CharField(required=True, validators=[validate_password])
    # confirm ở front

    def validate_old_password(self, value):
        user = self.instance
        if not user.check_password(value):
            raise serializers.ValidationError("Mật khẩu cũ không chính xác.")
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        instance.set_password(validated_data['new_password'])
        instance.save()
        return instance


# gui otp
class ResetPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email không tồn tại")
        return value


# xac nhan otp
class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True)

    def validate(self, attrs):
        email = attrs['email']
        otp = attrs['otp']

        cached_otp = cache.get(f"password_reset_otp:{email}")

        if cached_otp is None:
            raise serializers.ValidationError("OTP hết hạn hoặc không tồn tại.")

        if cached_otp != otp:
            raise serializers.ValidationError("OTP không chính xác.")

        return attrs


# reset mat khau
class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True)

    # tạm thời ko cần phức tạp
    # new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    # confirm ở front

    def validate(self, attrs):
        token = attrs.get('token')
        email = cache.get(f"reset_token:{token}")

        if not email:
            raise serializers.ValidationError("Token hết hạn hoặc không hợp lệ.")

        attrs['email'] = email
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        user = User.objects.get(email=self.validated_data['email'])
        user.set_password(self.validated_data['new_password'])
        user.save()

        return user


# cập nhật fcm
class UpdateFCMSerializer(serializers.Serializer):
    fcm_token = serializers.CharField(max_length=255)

    def validate_fcm_token(self, value):
        if not value or len(value) < 10:
            raise serializers.ValidationError("FCM token không hợp lệ")
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        if instance.fcm_token != validated_data['fcm_token']:
            instance.fcm_token = validated_data['fcm_token']
            instance.save()

        return instance
