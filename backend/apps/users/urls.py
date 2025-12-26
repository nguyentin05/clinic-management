from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import UserView, GoogleLoginView, PatientProfileView, ResetPasswordRequestView, VerifyOTPView, \
    ResetPasswordView

router = DefaultRouter()
router.register('', UserView, basename='users')
router.register('profile', PatientProfileView, basename='profile')

urlpatterns = [
    path('auth/google/', GoogleLoginView.as_view(), name='google-login'),
    path('auth/password-reset/request/', ResetPasswordRequestView.as_view(), name='request'),
    path('auth/password-reset/verify/', VerifyOTPView.as_view(), name='verify'),
    path('auth/password-reset/confirm/', ResetPasswordView.as_view(), name='confirm'),
    path('', include(router.urls)),
]
