from rest_framework import viewsets, generics

from apps.medical.models import TestOrder
from apps.medical.serializers import TestOrderSerializer


class TestOrderView(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveDestroyAPIView):
    queryset = TestOrder.objects.filter(active=True)
    serializer_class = TestOrderSerializer
