from datetime import timedelta

from drf_yasg import openapi

param_status = openapi.Parameter('status', openapi.IN_QUERY, description="Lọc theo trạng thái lịch hẹn",
                                 type=openapi.TYPE_STRING)
param_week_start = openapi.Parameter('week_start', openapi.IN_QUERY, description="Lọc từ ngày (YYYY-MM-DD)",
                                     type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE)
param_to_date = openapi.Parameter('to_date', openapi.IN_QUERY, description="Lọc đến ngày (YYYY-MM-DD)",
                                  type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE)
param_q = openapi.Parameter('q', openapi.IN_QUERY, description="Từ khóa tìm kiếm (tên dịch vụ)",
                            type=openapi.TYPE_STRING)

schedule_custom_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'mode': openapi.Schema(type=openapi.TYPE_STRING, description='Chế độ hiển thị: view (xem) hoặc edit (sửa)'),
        'week_start': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE,
                                     description="Ngày bắt đầu tuần"),
        'week_end': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE,
                                   description="Ngày kết thúc tuần"),
        'schedules': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT,
                                                                                  description="Danh sách lịch làm việc")),
    }
)


def get_monday_of_week(date):
    return date - timedelta(days=date.weekday())
