from rest_framework.serializers import ModelSerializer
from ..models import EquipmentHole


class BaseEquipmentHoleSerializer(ModelSerializer):
    class Meta:
        model = EquipmentHole
        fields = ['id', 'name']


class DetailEquipmentHoleSerializer(ModelSerializer):
    class Meta:
        model = EquipmentHole
        fields = ['id', 'name', 'normal_x', 'normal_y', 'normal_z', 'offset_x', 'offset_y', 'offset_z']


class CreateEquipmentHoleSerializer(ModelSerializer):
    class Meta:
        model = EquipmentHole
        fields = ['name', 'equipment', 'normal_x', 'normal_y', 'normal_z', 'offset_x', 'offset_y', 'offset_z']


class UpdateEquipmentHoleSerializer(ModelSerializer):
    class Meta:
        model = EquipmentHole
        fields = ['name', 'normal_x', 'normal_y', 'normal_z', 'offset_x', 'offset_y', 'offset_z']
