from django.urls import path

from clinic_management.urls import router
from .views import UserView, GoogleLoginView, ResetPasswordRequestView, VerifyOTPView, \
    ResetPasswordView, DoctorBookingView

router.register('users', UserView, basename='users')
router.register('doctors', DoctorBookingView, basename='doctors')

urlpatterns = [
    path('auth/google/', GoogleLoginView.as_view(), name='google-login'),
    path('auth/password-reset/request/', ResetPasswordRequestView.as_view(), name='request'),
    path('auth/password-reset/verify/', VerifyOTPView.as_view(), name='verify'),
    path('auth/password-reset/confirm/', ResetPasswordView.as_view(), name='confirm'),
]
