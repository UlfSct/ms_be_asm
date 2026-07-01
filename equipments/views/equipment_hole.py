from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.status import HTTP_200_OK
from rest_framework.response import Response

from be_asm_3d.permissions import IsAuthenticated
from ..filters import EquipmentHoleFilter
from ..models import EquipmentHole
from ..serializers import DetailEquipmentHoleSerializer, CreateEquipmentHoleSerializer, UpdateEquipmentHoleSerializer


class EquipmentHoleViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = None
    queryset = EquipmentHole.objects.all()
    serializer_class = DetailEquipmentHoleSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = EquipmentHoleFilter

    serializer_action_classes = {
        'create': CreateEquipmentHoleSerializer,
        'partial_update': UpdateEquipmentHoleSerializer,
    }

    def get_serializer_class(self):
        if hasattr(self, 'action') and self.action in self.serializer_action_classes:
            return self.serializer_action_classes[self.action]
        return DetailEquipmentHoleSerializer

    def get_queryset(self):
        return super().get_queryset()

    def list(self, request, *args, **kwargs):
        equipment_id = request.query_params.get('equipment')

        if equipment_id is None:
            return Response([], status=HTTP_200_OK)

        return super().list(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self.perform_destroy(self.get_object())
        return Response({}, status=HTTP_200_OK)
