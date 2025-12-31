from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.medical.models import TestOrder
from apps.medical.perms import IsNurse
from apps.medical.serializers import TestOrderSerializer


class TestOrderView(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveDestroyAPIView):
    queryset = TestOrder.objects.filter(active=True)
    serializer_class = TestOrderSerializer

    def get_permissions(self):
        if self.action == 'list':
            return [IsNurse()]
        return [IsAuthenticated()]

    def get_queryset(self):
        query = self.queryset

        s = self.request.query_params.get('status')
        if s:
            query = query.filter(status=s)

        return query.order_by('-created_date')


    @action(methods=['patch'], detail=True, url_path='update')
    def update_test_order(self, request, pk):
        test = self.get_object()

        serializer = TestOrderSerializer(test, data=request.data, context={'request': request}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)
