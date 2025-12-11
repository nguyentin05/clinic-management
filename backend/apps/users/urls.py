from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import UserView, GoogleLoginView

router = DefaultRouter()
router.register('', UserView, basename='users')

urlpatterns = [
    path('auth/google/', GoogleLoginView.as_view(), name='google-login'),
    path('', include(router.urls)),
]
