from django.db.models import OuterRef, Exists
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from be_asm_3d.utils import ReturnDeletedDataMixin
from ..models import Part, AssemblyPart
from ..serializers import PartDetailSerializer, PartCreateSerializer, PartUpdateSerializer, PartFullInfoSerializer


class PartViewSet(
    ReturnDeletedDataMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
    GenericViewSet
):
    queryset = Part.objects.all()
    permission_classes = [AllowAny]
    serializer_class = PartDetailSerializer

    serializer_action_classes = {
        'retrieve': PartDetailSerializer,
        'create': PartCreateSerializer,
        'partial_update': PartUpdateSerializer,
        'update': PartUpdateSerializer
    }

    def get_serializer_class(self):
        try:
            return self.serializer_action_classes[self.action]
        except (KeyError, AttributeError):
            return super().get_serializer_class()

    def get_queryset(self):
        return Part.objects.annotate(
            can_delete=~Exists(AssemblyPart.objects.filter(part_id=OuterRef('pk')))
        ).order_by('-updated')

    @action(detail=True, methods=['get'], url_path='full', url_name='full')
    def get_full_info(self, request, pk=None):
        part = self.get_object()

        part = Part.objects.prefetch_related(
            'coordinatesystem_set__plane_set',
            'plane_set'
        ).select_related(
            'material'
        ).get(id=part.id)

        serializer = PartFullInfoSerializer
        return Response(serializer(part).data)
