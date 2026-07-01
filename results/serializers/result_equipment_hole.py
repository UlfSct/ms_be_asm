from rest_framework.serializers import ModelSerializer

from results.models import ResultEquipmentHole


class ResultEquipmentHoleReadSerializer(ModelSerializer):
    class Meta:
        model = ResultEquipmentHole
        fields = [
            'id', 'normal_x', 'normal_y', 'normal_z',
            'offset_x', 'offset_y', 'offset_z'
        ]