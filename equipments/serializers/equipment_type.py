from rest_framework.serializers import ModelSerializer
from ..models import EquipmentType


class BaseEquipmentTypeSerializer(ModelSerializer):
    class Meta:
        model = EquipmentType
        fields = '__all__'


class CreateUpdateEquipmentTypeSerializer(ModelSerializer):
    class Meta:
        model = EquipmentType
        fields = ['name', 'file', 'is_active']
