from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.clinic.views import SpecialtyView, ServiceView

router = DefaultRouter()
router.register('specialties', SpecialtyView, basename='specialty')
router.register('services', ServiceView, basename='service')

urlpatterns = [
    path('', include(router.urls)),
]