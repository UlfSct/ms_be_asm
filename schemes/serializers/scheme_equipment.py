from rest_framework.serializers import ModelSerializer

from schemes.models import SchemeEquipment
from schemes.serializers.scheme_equipment_hole import SchemeEquipmentHoleReadSerializer


class SchemeEquipmentReadSerializer(ModelSerializer):
    holes = SchemeEquipmentHoleReadSerializer(read_only=True, many=True, source='schemes_equipment_holes')

    class Meta:
        model = SchemeEquipment
        fields = ['id', 'equipment', 'material', 'x', 'z', 'holes']
