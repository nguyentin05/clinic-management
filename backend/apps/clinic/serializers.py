from rest_framework import serializers

from apps.clinic.models import Specialty, Service, Appointment


class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = ['id', 'name']

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'price', 'duration_minutes', 'image', 'specialty']

    def to_representation(self, instance):
        data = super().to_representation(instance)

        data['image'] = instance.image.url if instance.image else ''

        return data

class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = []