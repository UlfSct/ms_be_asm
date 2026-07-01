from rest_framework.serializers import ModelSerializer

from schemes.models import SchemeEquipmentHole


class SchemeEquipmentHoleReadSerializer(ModelSerializer):

    class Meta:
        model = SchemeEquipmentHole
        fields = ['id', 'hole']