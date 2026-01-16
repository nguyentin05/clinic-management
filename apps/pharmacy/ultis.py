from drf_yasg import openapi

param_q = openapi.Parameter('q', openapi.IN_QUERY, description="Tìm kiếm theo tên thuốc", type=openapi.TYPE_STRING)
param_cate_id = openapi.Parameter('category_id', openapi.IN_QUERY, description="Lọc theo ID danh mục",
                                  type=openapi.TYPE_INTEGER)
param_date = openapi.Parameter('date', openapi.IN_QUERY, description="Lọc theo ngày (YYYY-MM-DD)",
                               type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE)
param_import_status = openapi.Parameter('status', openapi.IN_QUERY, description="Lọc theo trạng thái phiếu",
                                        type=openapi.TYPE_STRING)

detail_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'detail': openapi.Schema(type=openapi.TYPE_STRING, description='Thông báo kết quả hành động')
    }
)
