from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.models import Notification
from apps.notifications.perms import IsOwnerNotification
from apps.notifications.serializers import NotificationSerializer

from apps.notifications.services import NotificationService


# chưa phân quyền
class NotificationView(viewsets.ViewSet, generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, IsOwnerNotification]

    def get_queryset(self):
        query = Notification.objects.filter(recipient=self.request.user).select_related('recipient')

        is_read = self.request.query_params.get('is_read')
        if is_read:
            query = query.filter(is_read=is_read)

        notification_type = self.request.query_params.get('type')
        if notification_type:
            query = query.filter(NotificationType=notification_type)

        return query.order_by('-created_date')

    @action(methods=['patch'], detail=True, url_path='mark-as-read')
    def mark_as_read(self, request):
        notification = self.get_object()
        NotificationService.mark_as_read(notification.id, request.user)

        return Response({"message": "Đã đánh dấu thông báo"}, status=status.HTTP_200_OK)

    # api chỉ để lấy sl
    @action(methods=['get'], detail=False, url_path='unread-count')
    def get_unread_count(self, request):
        return Response({"unread_count": NotificationService.get_unread_count(request.user)},
                        status=status.HTTP_200_OK)
