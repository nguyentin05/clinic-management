from rest_framework.pagination import PageNumberPagination


class MedicinePaginator(PageNumberPagination):
    page_size = 8