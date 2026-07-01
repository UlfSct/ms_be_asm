from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import ListModelMixin
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.status import HTTP_200_OK
from rest_framework.response import Response

from be_asm_3d.permissions import IsAdmin, IsAuthenticated
from be_asm_3d.utils import DefaultPagination
from ..filters import EquipmentTypeFilter
from ..models import EquipmentType
from ..serializers import BaseEquipmentTypeSerializer, CreateUpdateEquipmentTypeSerializer


class AdminEquipmentTypeViewSet(ModelViewSet):
    permission_classes = [IsAdmin]
    pagination_class = DefaultPagination
    queryset = EquipmentType.objects.all()
    serializer_class = BaseEquipmentTypeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = EquipmentTypeFilter

    serializer_action_classes = {
        'list': BaseEquipmentTypeSerializer,
        'create': CreateUpdateEquipmentTypeSerializer,
        'partial_update': CreateUpdateEquipmentTypeSerializer,
    }

    def get_serializer_class(self):
        if hasattr(self, 'action') and self.action in self.serializer_action_classes:
            return self.serializer_action_classes[self.action]

        return BaseEquipmentTypeSerializer

    def destroy(self, request, *args, **kwargs):
        self.perform_destroy(self.get_object())
        return Response({}, status=HTTP_200_OK)


class EquipmentTypeViewSet(ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]
    queryset = EquipmentType.objects.all()
    serializer_class = BaseEquipmentTypeSerializer
    pagination_class = None

    def get_queryset(self):
        return EquipmentType.objects.all().filter(is_active=True)
