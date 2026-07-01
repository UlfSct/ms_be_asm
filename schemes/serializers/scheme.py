from django.db.models import Q
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer, Serializer

from schemes.models import Scheme, SchemeEquipmentHole, SchemeConnection
from schemes.serializers.scheme_connection import SchemeConnectionReadSerializer
from schemes.serializers.scheme_equipment import SchemeEquipmentReadSerializer


class BaseSchemeSerializer(ModelSerializer):
    class Meta:
        model = Scheme
        fields = ['id', 'name', 'description', 'created', 'updated']


class CreateUpdateSchemeSerializer(ModelSerializer):
    class Meta:
        model = Scheme
        fields = ['name', 'description']


class SchemeFullSerializer(Serializer):
    equipments = SerializerMethodField()
    connections = SerializerMethodField()

    def get_equipments(self, scheme):
        return SchemeEquipmentReadSerializer(scheme.schemes_equipments.all(), many=True).data

    def get_connections(self, scheme):
        scheme_equipment_ids = scheme.schemes_equipments.values_list('id', flat=True)
        scheme_hole_ids = SchemeEquipmentHole.objects.filter(
            scheme_equipment_id__in=scheme_equipment_ids
        ).values_list('id', flat=True)
        connections = SchemeConnection.objects.filter(
            Q(scheme_equipment_hole_start_id__in=scheme_hole_ids) |
            Q(scheme_equipment_hole_end_id__in=scheme_hole_ids)
        ).distinct()
        return SchemeConnectionReadSerializer(connections, many=True).data
