from drf_yasg.utils import swagger_auto_schema, no_body
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.models import Notification
from apps.notifications.perms import IsOwnerNotification
from apps.notifications.serializers import NotificationSerializer
from apps.notifications.services import NotificationService
from apps.notifications.ultis import param_is_read, param_notif_type, message_response, unread_count_response


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

    @swagger_auto_schema(
        manual_parameters=[param_is_read, param_notif_type],
        operation_description="Lấy danh sách thông báo của người dùng (Có thể lọc theo trạng thái và loại)"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description='Đánh dấu một thông báo là đã đọc',
        request_body=no_body,
        responses={status.HTTP_200_OK: message_response}
    )
    @action(methods=['patch'], detail=True, url_path='mark-as-read')
    def mark_as_read(self, request, pk):
        notification = self.get_object()
        NotificationService.mark_as_read(notification.id, request.user)

        return Response({"message": "Đã đánh dấu thông báo"}, status=status.HTTP_200_OK)

    # api chỉ để lấy sl
    @swagger_auto_schema(
        operation_description='Lấy số lượng thông báo chưa đọc',
        responses={status.HTTP_200_OK: unread_count_response}
    )
    @action(methods=['get'], detail=False, url_path='unread-count')
    def get_unread_count(self, request):
        return Response({"unread_count": NotificationService.get_unread_count(request.user)},
                        status=status.HTTP_200_OK)
