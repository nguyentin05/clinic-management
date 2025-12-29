from rest_framework.pagination import PageNumberPagination


class ServicePaginator(PageNumberPagination):
    page_size = 5

class AppointmentPaginator(PageNumberPagination):
    page_size = 5