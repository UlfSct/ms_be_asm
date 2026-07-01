from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Prefetch, Q, Value, Exists, OuterRef, BooleanField
from django.db.models.functions import JSONObject
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from be_asm_3d.utils import ReturnDeletedDataMixin
from ..models import Assembly, AssemblyPart
from ..serializers import AssemblyDetailSerializer, AssemblyCreateSerializer, AssemblyUpdateSerializer, \
    AssemblyFullInfoSerializer


class AssemblyViewSet(
    ReturnDeletedDataMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
    GenericViewSet
):
    queryset = Assembly.objects.all()
    permission_classes = [AllowAny]
    serializer_class = AssemblyDetailSerializer

    serializer_action_classes = {
        'retrieve': AssemblyDetailSerializer,
        'create': AssemblyCreateSerializer,
        'partial_update': AssemblyUpdateSerializer,
        'update': AssemblyUpdateSerializer,
    }

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action == 'retrieve':
            queryset = queryset.annotate(
                parts=ArrayAgg(
                    JSONObject(
                        id='assemblypart__part__id',
                        name='assemblypart__part__name',
                        material_name='assemblypart__part__material__name'
                    ),
                    filter=Q(assemblypart__part__isnull=False),
                    distinct=True,
                    default=Value([])
                ),
                can_delete=Value(True, output_field=BooleanField())
            )
        return queryset

    def get_serializer_class(self):
        try:
            return self.serializer_action_classes[self.action]
        except (KeyError, AttributeError):
            return super().get_serializer_class()

    @action(detail=True, methods=['get'], url_path='full', url_name='full')
    def get_full_info(self, request, pk=None):
        assembly = self.get_object()

        assembly = Assembly.objects.prefetch_related(
            'coordinatesystem_set__plane_set',
            'plane_set'
        ).get(id=assembly.id)

        serializer = AssemblyFullInfoSerializer
        return Response(serializer(assembly).data)
