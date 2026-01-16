from drf_yasg import openapi

param_is_read = openapi.Parameter(
    'is_read',
    openapi.IN_QUERY,
    description="Lọc trạng thái: true (đã đọc) hoặc false (chưa đọc)",
    type=openapi.TYPE_BOOLEAN
)

param_notif_type = openapi.Parameter(
    'type',
    openapi.IN_QUERY,
    description="Lọc theo loại thông báo",
    type=openapi.TYPE_STRING
)

unread_count_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'unread_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Số lượng tin chưa đọc')
    }
)

message_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'message': openapi.Schema(type=openapi.TYPE_STRING, example='Đã đánh dấu thông báo')
    }
)
