from django.db.models import Q, Case, When, Value, BooleanField, OuterRef, Exists
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from be_asm_3d.permissions import IsAuthenticated, IsAdmin
from be_asm_3d.utils import DefaultPagination
from schemes.models import SchemeEquipment
from ..filters import EquipmentFilter
from ..models import Equipment
from ..serializers import EquipmentDetailSerializer, EquipmentListSerializer, EquipmentCreateSerializer, \
    EquipmentUpdateSerializer, BaseEquipmentSerializer, AdminEquipmentListSerializer, AdminEquipmentCreateSerializer, \
    AdminEquipmentUpdateSerializer, AdminEquipmentDetailSerializer


class EquipmentViewSet(ModelViewSet):
    queryset = Equipment.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination
    serializer_class = EquipmentDetailSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = EquipmentFilter

    serializer_action_classes = {
        'list': EquipmentListSerializer,
        'retrieve': EquipmentDetailSerializer,
        'create': EquipmentCreateSerializer,
        'partial_update': EquipmentUpdateSerializer,
    }

    def get_serializer_class(self):
        if hasattr(self, 'action') and self.action in self.serializer_action_classes:
            return self.serializer_action_classes[self.action]

        return EquipmentDetailSerializer

    def get_queryset(self):
        user = self.request.user

        team_equipments = Equipment.objects.filter(
            user__team_memberships__team__members__user=user,
            share=True
        )

        queryset = super().get_queryset().filter(
            Q(is_global=True) |
            Q(user=user) |
            Q(pk__in=team_equipments)
        ).distinct()

        queryset = queryset.annotate(
            can_delete=~Exists(SchemeEquipment.objects.filter(equipment=OuterRef('pk'))),
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
        equipment = self.get_object()

        if equipment.is_global:
            return Response({"detail": "Удалять глобальное оборудование может только администратор"},
                            status=status.HTTP_403_FORBIDDEN)
        if not equipment.can_delete:
            return Response({"detail": "Оборудование уже используется в некоторых схемах"},
                            status=status.HTTP_409_CONFLICT)

        self.perform_destroy(equipment)
        return Response({}, status=status.HTTP_200_OK)

    @action(methods=['GET'], detail=False, name='selector')
    def selector(self, request, *args, **kwargs):
        return Response(BaseEquipmentSerializer(Equipment.objects.all(), many=True).data)


class AdminEquipmentViewSet(ModelViewSet):
    queryset = Equipment.objects.all()
    permission_classes = [IsAdmin]
    pagination_class = DefaultPagination
    serializer_class = EquipmentDetailSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = EquipmentFilter

    serializer_action_classes = {
        'list': AdminEquipmentListSerializer,
        'retrieve': AdminEquipmentDetailSerializer,
        'create': AdminEquipmentCreateSerializer,
        'partial_update': AdminEquipmentUpdateSerializer,
    }

    def get_serializer_class(self):
        if hasattr(self, 'action') and self.action in self.serializer_action_classes:
            return self.serializer_action_classes[self.action]

        return AdminEquipmentDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset().filter(is_global=True)
        return queryset.annotate(
            can_delete=~Exists(SchemeEquipment.objects.filter(equipment=OuterRef('pk'))),
        ).order_by('-updated')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, is_global=True)

    def destroy(self, request, *args, **kwargs):
        equipment = self.get_object()

        if not equipment.can_delete:
            return Response({"detail": "Оборудование уже используется в некоторых схемах"},
                            status=status.HTTP_409_CONFLICT)

        self.perform_destroy(equipment)
        return Response({}, status=status.HTTP_200_OK)
