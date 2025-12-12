from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import UserView, GoogleLoginView, ResetPasswordRequestView, ResetPasswordConfirmView

router = DefaultRouter()
router.register('', UserView, basename='users')

urlpatterns = [
    path('auth/google/', GoogleLoginView.as_view(), name='google-login'),
    path('password-reset/', ResetPasswordRequestView.as_view(), name='password-reset-request'),
    path('password-reset-confirm/', ResetPasswordConfirmView.as_view(), name='password-reset-confirm'),
    path('', include(router.urls)),
]
