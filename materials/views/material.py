from django.db.models import Exists, OuterRef, Q, Case, When, Value, BooleanField
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from be_asm_3d.permissions import IsAuthenticated, IsAdmin
from be_asm_3d.utils import DefaultPagination
from model_constructor.models import Part
from ..filters import MaterialFilter
from ..models import Material
from ..serializers import MaterialDetailSerializer, MaterialListSerializer, MaterialCreateSerializer, \
    MaterialUpdateSerializer, BaseMaterialSerializer, AdminMaterialListSerializer, AdminMaterialCreateSerializer, \
    AdminMaterialUpdateSerializer, AdminMaterialDetailSerializer


class MaterialViewSet(ModelViewSet):
    queryset = Material.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination
    serializer_class = MaterialDetailSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = MaterialFilter

    serializer_action_classes = {
        'list': MaterialListSerializer,
        'retrieve': MaterialDetailSerializer,
        'create': MaterialCreateSerializer,
        'partial_update': MaterialUpdateSerializer,
    }

    def get_serializer_class(self):
        if hasattr(self, 'action') and self.action in self.serializer_action_classes:
            return self.serializer_action_classes[self.action]

        return MaterialDetailSerializer

    def get_queryset(self):
        user = self.request.user

        team_materials = Material.objects.filter(
            user__team_memberships__team__members__user=user,
            share=True
        )

        queryset = super().get_queryset().filter(
            Q(is_global=True) |
            Q(user=user) |
            Q(pk__in=team_materials)
        ).distinct()

        queryset = queryset.annotate(
            can_delete=~Exists(Part.objects.filter(material=OuterRef('pk'))),
            is_mine=Case(
                When(user=user, then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            )
        )

        return queryset.order_by('-updated')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        material = self.get_object()

        if material.is_global:
            return Response({"detail": "Удалять глобальные материалы может только администратор"}, status=status.HTTP_403_FORBIDDEN)
        if not material.can_delete:
            return Response({"detail": "Материал уже используется в некоторых деталях"}, status=status.HTTP_409_CONFLICT)

        self.perform_destroy(material)
        return Response({}, status=status.HTTP_200_OK)

    @action(methods=['GET'], detail=False, name='selector')
    def selector(self, request, *args, **kwargs):
        return Response(BaseMaterialSerializer(Material.objects.all(), many=True).data)


class AdminMaterialViewSet(ModelViewSet):
    queryset = Material.objects.all()
    permission_classes = [IsAdmin]
    pagination_class = DefaultPagination
    serializer_class = MaterialDetailSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = MaterialFilter

    serializer_action_classes = {
        'list': AdminMaterialListSerializer,
        'retrieve': AdminMaterialDetailSerializer,
        'create': AdminMaterialCreateSerializer,
        'partial_update': AdminMaterialUpdateSerializer,
    }

    def get_serializer_class(self):
        if hasattr(self, 'action') and self.action in self.serializer_action_classes:
            return self.serializer_action_classes[self.action]

        return AdminMaterialDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset().filter(is_global=True)
        return queryset.annotate(
            can_delete=~Exists(Part.objects.filter(material=OuterRef('pk')))
        ).order_by('-updated')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, is_global=True)

    def destroy(self, request, *args, **kwargs):
        material = self.get_object()

        if not material.can_delete:
            return Response({"detail": "Материал уже используется в некоторых деталях"}, status=status.HTTP_409_CONFLICT)

        self.perform_destroy(material)
        return Response({}, status=status.HTTP_200_OK)
