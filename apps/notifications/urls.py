from apps.notifications.views import NotificationView
from clinic_management.urls import router

router.register('notifications', NotificationView, basename='notifications')

urlpatterns = [

]