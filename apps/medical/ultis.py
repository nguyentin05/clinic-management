from drf_yasg import openapi

param_test_status = openapi.Parameter(
    'status',
    openapi.IN_QUERY,
    description="Lọc theo trạng thái xét nghiệm",
    type=openapi.TYPE_STRING
)