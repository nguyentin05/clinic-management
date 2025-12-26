from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.clinic import paginators
from apps.clinic.models import Specialty, Service
from apps.clinic.serializers import SpecialtySerializer, ServiceSerializer


class SpecialtyView(viewsets.ViewSet, generics.ListAPIView):
    queryset = Specialty.objects.filter(active=True)
    serializer_class = SpecialtySerializer

    @action(methods=['get'], detail=True, url_path='services')
    def get_services(self, request, pk):
        services = self.get_object().services.filter(active=True)

        p = paginators.ServicePaginator()
        page = p.paginate_queryset(services, self.request)

        if page is not None:
            serializer = ServiceSerializer(page, many=True)
            return p.get_paginated_response(serializer.data)

        return Response(ServiceSerializer(services, many=True).data, status=status.HTTP_200_OK)

class ServiceView(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView):
    queryset = Service.objects.filter(active=True)
    serializer_class = ServiceSerializer
    pagination_class = paginators.ServicePaginator

    def get_queryset(self):
        query = self.queryset

        q = self.request.query_params.get('q')
        if q:
            query = query.filter(name__icontains=q)

        return query