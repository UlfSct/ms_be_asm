from django.db.models import Exists, OuterRef, Q, Case, When, Value, BooleanField
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from be_asm_3d.permissions import IsAuthenticated, IsAdmin
from be_asm_3d.utils import DefaultPagination
from equipments.models import Equipment
from ..filters import ModelFilter
from ..models import Model3D
from ..serializers import ModelDetailSerializer, ModelListSerializer, ModelCreateSerializer, \
    ModelUpdateSerializer, BaseModelSerializer, AdminModelListSerializer, AdminModelCreateSerializer, \
    AdminModelUpdateSerializer, AdminModelDetailSerializer


class Model3DViewSet(ModelViewSet):
    queryset = Model3D.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination
    serializer_class = ModelDetailSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ModelFilter

    serializer_action_classes = {
        'list': ModelListSerializer,
        'retrieve': ModelDetailSerializer,
        'create': ModelCreateSerializer,
        'partial_update': ModelUpdateSerializer,
    }

    def get_serializer_class(self):
        if hasattr(self, 'action') and self.action in self.serializer_action_classes:
            return self.serializer_action_classes[self.action]

        return ModelDetailSerializer

    def get_queryset(self):
        user = self.request.user

        team_models = Model3D.objects.filter(
            user__team_memberships__team__members__user=user,
            share=True
        )

        queryset = super().get_queryset().filter(
            Q(is_global=True) |
            Q(user=user) |
            Q(pk__in=team_models)
        ).distinct()

        queryset = queryset.annotate(
            can_delete=~Exists(Equipment.objects.filter(model=OuterRef('pk'))),
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
        model = self.get_object()

        if model.is_global:
            return Response({"detail": "Удалять глобальные модели может только администратор"}, status=status.HTTP_403_FORBIDDEN)
        if not model.can_delete:
            return Response({"detail": "Материал уже используется в некоторых аппаратах"}, status=status.HTTP_409_CONFLICT)

        self.perform_destroy(model)
        return Response({}, status=status.HTTP_200_OK)

    @action(methods=['GET'], detail=False, name='selector')
    def selector(self, request, *args, **kwargs):
        return Response(BaseModelSerializer(Model3D.objects.all(), many=True).data)


class AdminModel3DViewSet(ModelViewSet):
    queryset = Model3D.objects.all()
    permission_classes = [IsAdmin]
    pagination_class = DefaultPagination
    serializer_class = ModelDetailSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ModelFilter

    serializer_action_classes = {
        'list': AdminModelListSerializer,
        'retrieve': AdminModelDetailSerializer,
        'create': AdminModelCreateSerializer,
        'partial_update': AdminModelUpdateSerializer,
    }

    def get_serializer_class(self):
        if hasattr(self, 'action') and self.action in self.serializer_action_classes:
            return self.serializer_action_classes[self.action]

        return AdminModelDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset().filter(is_global=True)
        return queryset.annotate(
            can_delete=~Exists(Equipment.objects.filter(model=OuterRef('pk')))
        ).order_by('-updated')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, is_global=True)

    def destroy(self, request, *args, **kwargs):
        model = self.get_object()

        if not model.can_delete:
            return Response({"detail": "Материал уже используется в некоторых аппаратах"}, status=status.HTTP_409_CONFLICT)

        self.perform_destroy(model)
        return Response({}, status=status.HTTP_200_OK)
