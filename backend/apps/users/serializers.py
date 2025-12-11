from rest_framework import serializers
from .models import User, Role, PatientProfile, DoctorProfile, StaffProfile


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
        extra_kwargs = {
            'password': {
                'write_only': True
            }
        }

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(user.password)
        user.role = Role.PATIENT
        user.save()

        return user