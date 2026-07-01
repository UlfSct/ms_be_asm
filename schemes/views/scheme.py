import os

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_201_CREATED
from rest_framework.response import Response

from be_asm_3d.permissions import IsAuthenticated
from be_asm_3d.utils import DefaultPagination
from results.models import ResultConnectionPoint, ResultConnection, ResultEquipmentHole, ResultEquipment, Result
from ..filters import SchemeFilter
from ..models import Scheme, SchemeConnection, SchemeEquipmentHole, SchemeConnectionPoint, SchemeEquipment
from ..serializers import BaseSchemeSerializer, CreateUpdateSchemeSerializer, SchemeFullSerializer


class SchemeViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination
    queryset = Scheme.objects.all()
    serializer_class = BaseSchemeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SchemeFilter

    serializer_action_classes = {
        'list': BaseSchemeSerializer,
        'retrieve': BaseSchemeSerializer,
        'create': CreateUpdateSchemeSerializer,
        'partial_update': CreateUpdateSchemeSerializer,
    }

    def get_serializer_class(self):
        if hasattr(self, 'action') and self.action in self.serializer_action_classes:
            return self.serializer_action_classes[self.action]

        return BaseSchemeSerializer

    def get_queryset(self):
        return super().get_queryset().filter(Q(user=self.request.user))

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        self.perform_destroy(self.get_object())
        return Response({}, status=HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='full', url_name='full')
    def full(self, request, pk=None):
        scheme = self.get_object()
        serializer = SchemeFullSerializer(scheme)
        return Response(serializer.data, status=HTTP_200_OK)

    @action(detail=True, methods=['put'], url_path='full')
    def full_update(self, request, pk=None):
        scheme = self.get_object()
        data = request.data

        # Базовая валидация структуры
        if 'equipments' not in data or 'connections' not in data:
            return Response(
                {"detail": "Fields 'equipments' and 'connections' are required."},
                status=HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                temp_eq_mapping = {}
                temp_hole_mapping = {}
                temp_conn_mapping = {}

                processed_eq_ids = self._update_equipments(
                    scheme, data['equipments'], temp_eq_mapping, temp_hole_mapping
                )

                processed_conn_ids = self._update_connections(
                    scheme, data['connections'], temp_hole_mapping, temp_conn_mapping
                )

                self._delete_absent_connections(scheme, processed_conn_ids)

                self._delete_absent_equipments(scheme, processed_eq_ids)

        except (ValueError, ValidationError, KeyError) as e:
            return Response({"detail": str(e)}, status=HTTP_400_BAD_REQUEST)

        serializer = SchemeFullSerializer(scheme)
        return Response(serializer.data, status=HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='convert-to-result')
    def convert_to_result(self, request, pk=None):
        scheme = self.get_object()
        name = request.data.get('name')
        if not name or not name.strip():
            return Response(
                {'name': 'Название обязательно и не может быть пустым.'},
                status=HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # 1. Создаём Result
                result = Result.objects.create(
                    name=name,
                    user=request.user
                )

                # Маппинги для связи объектов
                scheme_eq_to_result_eq = {}
                scheme_hole_to_result_hole = {}

                # 2. Обработка оборудований схемы
                for scheme_eq in scheme.schemes_equipments.select_related(
                        'equipment', 'material'
                ).prefetch_related('schemes_equipment_holes__hole'):
                    equipment = scheme_eq.equipment
                    material = scheme_eq.material

                    # Копирование файла модели
                    old_file = equipment.model.file
                    new_file_name = default_storage.generate_filename(
                        os.path.join('result_models', os.path.basename(old_file.name))
                    )
                    new_file_path = default_storage.save(new_file_name, ContentFile(old_file.read()))

                    result_eq = ResultEquipment.objects.create(
                        result=result,
                        model=new_file_path,
                        x=scheme_eq.x,
                        y=0.0,
                        z=scheme_eq.z,
                        rotate_y=0.0,
                        base_color=material.base_color,
                        reflectivity=material.reflectivity,
                        transparency=material.transparency,
                        shininess=material.shininess,
                        width=equipment.model.width,
                        height=equipment.model.height,
                        depth=equipment.model.depth,
                    )
                    scheme_eq_to_result_eq[scheme_eq.id] = result_eq

                    # 3. Обработка отверстий оборудования схемы
                    for scheme_hole in scheme_eq.schemes_equipment_holes.all():
                        hole = scheme_hole.hole
                        result_hole = ResultEquipmentHole.objects.create(
                            result_equipment=result_eq,
                            normal_x=hole.normal_x,
                            normal_y=hole.normal_y,
                            normal_z=hole.normal_z,
                            offset_x=hole.offset_x,
                            offset_y=hole.offset_y,
                            offset_z=hole.offset_z,
                        )
                        scheme_hole_to_result_hole[scheme_hole.id] = result_hole

                # 4. Обработка соединений схемы
                connections = SchemeConnection.objects.filter(
                    Q(scheme_equipment_hole_start__scheme_equipment__scheme=scheme) |
                    Q(scheme_equipment_hole_end__scheme_equipment__scheme=scheme)
                ).distinct().select_related('material',
                                            'scheme_equipment_hole_start__scheme_equipment',
                                            'scheme_equipment_hole_end__scheme_equipment'
                                            )

                for scheme_conn in connections:
                    start_hole_id = scheme_conn.scheme_equipment_hole_start_id
                    end_hole_id = scheme_conn.scheme_equipment_hole_end_id
                    start_result_hole = scheme_hole_to_result_hole.get(start_hole_id)
                    end_result_hole = scheme_hole_to_result_hole.get(end_hole_id)

                    if not start_result_hole or not end_result_hole:
                        raise ValidationError(
                            f'Не найдено соответствующее отверстие для соединения схемы id={scheme_conn.id}'
                        )

                    material = scheme_conn.material
                    result_conn = ResultConnection.objects.create(
                        result_equipment_hole_start=start_result_hole,
                        result_equipment_hole_end=end_result_hole,
                        base_color=material.base_color,
                        reflectivity=material.reflectivity,
                        transparency=material.transparency,
                        shininess=material.shininess,
                        r=scheme_conn.r,
                    )

                    # Точки соединения: на основе координат оборудования и смещений отверстий
                    start_eq = start_result_hole.result_equipment
                    end_eq = end_result_hole.result_equipment

                    # Точка начала (index=0)
                    ResultConnectionPoint.objects.create(
                        connection=result_conn,
                        index=0,
                        x=start_eq.x + start_result_hole.offset_x,
                        y=start_eq.y + start_result_hole.offset_y,
                        z=start_eq.z + start_result_hole.offset_z,
                    )

                    # Точка конца (index=1)
                    ResultConnectionPoint.objects.create(
                        connection=result_conn,
                        index=1,
                        x=end_eq.x + end_result_hole.offset_x,
                        y=end_eq.y + end_result_hole.offset_y,
                        z=end_eq.z + end_result_hole.offset_z,
                    )

                return Response(
                    {'id': result.id, 'name': result.name},
                    status=HTTP_201_CREATED
                )

        except Exception as e:
            return Response(
                {'detail': f'Ошибка при создании результата: {str(e)}'},
                status=HTTP_400_BAD_REQUEST
            )

    def _update_equipments(self, scheme, equipments_data, temp_eq_mapping, temp_hole_mapping):
        current_equipments = {eq.id: eq for eq in scheme.schemes_equipments.all()}
        processed_eq_ids = set()

        for eq_data in equipments_data:
            eq_id = eq_data.get('id')
            if eq_id is None:
                raise ValueError("Each equipment must have an 'id' field.")

            equipment_type_id = eq_data.get('equipment')
            material_id = eq_data.get('material')
            if equipment_type_id is None or material_id is None:
                raise ValueError("Each equipment must have 'equipment' and 'material' fields.")

            self._check_foreign_key_exists('equipments.Equipment', equipment_type_id)
            self._check_foreign_key_exists('materials.Material', material_id)

            x = eq_data.get('x')
            z = eq_data.get('z')
            if x is None or z is None:
                raise ValueError("Each equipment must have 'x' and 'z' fields.")

            if isinstance(eq_id, int):
                equipment = current_equipments.get(eq_id)
                if not equipment:
                    raise ValueError(f"Equipment with id={eq_id} not found for update.")

                equipment.equipment_id = equipment_type_id
                equipment.material_id = material_id
                equipment.x = x
                equipment.z = z
                equipment.save()
                current_equipments.pop(eq_id, None)
            else:
                equipment = SchemeEquipment.objects.create(
                    scheme=scheme,
                    equipment_id=equipment_type_id,
                    material_id=material_id,
                    x=x,
                    z=z
                )
                temp_eq_mapping[eq_id] = equipment.id

            processed_eq_ids.add(equipment.id)

            holes_data = eq_data.get('holes', [])
            current_holes = {hole.id: hole for hole in equipment.schemes_equipment_holes.all()}
            processed_hole_ids = set()

            for hole_data in holes_data:
                hole_id = hole_data.get('id')
                if hole_id is None:
                    raise ValueError("Each hole must have an 'id' field.")

                hole_ref_id = hole_data.get('hole')
                if hole_ref_id is None:
                    raise ValueError("Each hole must have a 'hole' field.")
                self._check_foreign_key_exists('equipments.EquipmentHole', hole_ref_id)

                if isinstance(hole_id, int):
                    hole = current_holes.get(hole_id)
                    if not hole:
                        raise ValueError(f"Hole with id={hole_id} not found for update.")
                    hole.hole_id = hole_ref_id
                    hole.save()
                    current_holes.pop(hole_id, None)
                else:
                    hole = SchemeEquipmentHole.objects.create(
                        scheme_equipment=equipment,
                        hole_id=hole_ref_id
                    )
                    temp_hole_mapping[hole_id] = hole.id

                processed_hole_ids.add(hole.id)

            if processed_hole_ids:
                equipment.schemes_equipment_holes.exclude(id__in=processed_hole_ids).delete()
            else:
                equipment.schemes_equipment_holes.all().delete()

        return processed_eq_ids

    def _update_connections(self, scheme, connections_data, temp_hole_mapping, temp_conn_mapping):
        current_connections = {
            conn.id: conn for conn in SchemeConnection.objects.filter(
                Q(scheme_equipment_hole_start__scheme_equipment__scheme=scheme) |
                Q(scheme_equipment_hole_end__scheme_equipment__scheme=scheme)
            ).distinct()
        }
        processed_conn_ids = set()

        for conn_data in connections_data:
            conn_id = conn_data.get('id')
            if conn_id is None:
                raise ValueError("Each connection must have an 'id' field.")
            conn_r = conn_data.get('r') or 20.0

            material_id = conn_data.get('material')
            if material_id is None:
                raise ValueError("Each connection must have a 'material' field.")
            self._check_foreign_key_exists('materials.Material', material_id)

            start_hole = self._resolve_hole_id(conn_data.get('scheme_equipment_hole_start'), temp_hole_mapping)
            end_hole = self._resolve_hole_id(conn_data.get('scheme_equipment_hole_end'), temp_hole_mapping)

            if isinstance(conn_id, int):
                connection = current_connections.get(conn_id)
                if not connection:
                    raise ValueError(f"Connection with id={conn_id} not found for update.")
                connection.scheme_equipment_hole_start_id = start_hole
                connection.scheme_equipment_hole_end_id = end_hole
                connection.material_id = material_id
                connection.r = conn_r
                connection.save()
                current_connections.pop(conn_id, None)
            else:
                connection = SchemeConnection.objects.create(
                    scheme_equipment_hole_start_id=start_hole,
                    scheme_equipment_hole_end_id=end_hole,
                    material_id=material_id,
                    r=conn_r
                )
                temp_conn_mapping[conn_id] = connection.id

            processed_conn_ids.add(connection.id)

            points_data = conn_data.get('points', [])
            current_points = {point.id: point for point in connection.schemes_connection_points.all()}
            processed_point_ids = set()

            for point_data in points_data:
                point_id = point_data.get('id')
                if point_id is None:
                    raise ValueError("Each point must have an 'id' field.")

                idx = point_data.get('index')
                x = point_data.get('x')
                z = point_data.get('z')
                if idx is None or x is None or z is None:
                    raise ValueError("Each point must have 'index', 'x', 'z' fields.")

                if isinstance(point_id, int):
                    point = current_points.get(point_id)
                    if not point:
                        raise ValueError(f"Point with id={point_id} not found for update.")
                    point.index = idx
                    point.x = x
                    point.z = z
                    point.save()
                    current_points.pop(point_id, None)
                else:
                    SchemeConnectionPoint.objects.create(
                        connection=connection,
                        index=idx,
                        x=x,
                        z=z
                    )

            if processed_point_ids:
                connection.schemes_connection_points.exclude(id__in=processed_point_ids).delete()
            else:
                connection.schemes_connection_points.all().delete()

        return processed_conn_ids

    def _resolve_hole_id(self, hole_ref, temp_hole_mapping):
        if hole_ref is None:
            raise ValueError("scheme_equipment_hole_start and scheme_equipment_hole_end are required.")
        if isinstance(hole_ref, int):
            return hole_ref
        else:
            real_id = temp_hole_mapping.get(hole_ref)
            if real_id is None:
                raise ValueError(f"Temporary hole id '{hole_ref}' not found in created holes.")
            return real_id

    def _delete_absent_connections(self, scheme, processed_conn_ids):
        connections_to_delete = SchemeConnection.objects.filter(
            Q(scheme_equipment_hole_start__scheme_equipment__scheme=scheme) |
            Q(scheme_equipment_hole_end__scheme_equipment__scheme=scheme)
        ).distinct()
        if processed_conn_ids:
            connections_to_delete = connections_to_delete.exclude(id__in=processed_conn_ids)
        connections_to_delete.delete()

    def _delete_absent_equipments(self, scheme, processed_eq_ids):
        equipments_to_delete = scheme.schemes_equipments.all()
        if processed_eq_ids:
            equipments_to_delete = equipments_to_delete.exclude(id__in=processed_eq_ids)
        equipments_to_delete.delete()

    def _check_foreign_key_exists(self, app_label_model, obj_id):
        from django.apps import apps
        try:
            model = apps.get_model(app_label_model)
            if not model.objects.filter(id=obj_id).exists():
                raise ValueError(f"{model.__name__} with id={obj_id} does not exist.")
        except LookupError:
            pass
