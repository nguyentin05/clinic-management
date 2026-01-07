from rest_framework import serializers
from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'type', 'type_display', 'title', 'message',
                  'metadata', 'is_read', 'created_date']

#seri cho thông báo của bên websocket
class NotificationWebSocketSerializer:
    @staticmethod
    def serialize(notification):
        return {
            "id": notification.id,
            "type": notification.type,
            "type_display": notification.get_type_display(),
            "title": notification.title,
            "message": notification.message,
            "metadata": notification.metadata,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat(),
        }
