from django.db.models import Q
from rest_framework import serializers

from results.models import Result, ResultEquipmentHole, ResultConnection
from results.serializers.result_connection import ResultConnectionReadSerializer
from results.serializers.result_equipment import ResultEquipmentReadSerializer


class BaseResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Result
        fields = ['id', 'name', 'created', 'updated', 'is_optimizing']


class ResultFullSerializer(serializers.Serializer):
    equipments = serializers.SerializerMethodField()
    connections = serializers.SerializerMethodField()

    def get_equipments(self, result):
        equipments = result.result_equipments.all()
        return ResultEquipmentReadSerializer(
            equipments, many=True, context=self.context
        ).data

    def get_connections(self, result):
        # Получаем все отверстия, принадлежащие оборудованию этого результата
        result_hole_ids = ResultEquipmentHole.objects.filter(
            result_equipment__result=result
        ).values_list('id', flat=True)
        # Соединения, которые начинаются или заканчиваются в этих отверстиях
        connections = ResultConnection.objects.filter(
            Q(result_equipment_hole_start_id__in=result_hole_ids) |
            Q(result_equipment_hole_end_id__in=result_hole_ids)
        ).distinct()
        return ResultConnectionReadSerializer(
            connections, many=True, context=self.context
        ).data