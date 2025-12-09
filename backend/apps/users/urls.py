from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import RegisterView, UserViewSet

router = DefaultRouter()
router.register(r'', UserViewSet, basename='users')

urlpatterns = [
    path('register/', RegisterView.as_view({'post': 'create'}), name='register'),
    path('', include(router.urls)),
]
