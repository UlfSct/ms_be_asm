from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer

from results.models import ResultEquipment
from results.serializers.result_equipment_hole import ResultEquipmentHoleReadSerializer


class ResultEquipmentReadSerializer(ModelSerializer):
    holes = ResultEquipmentHoleReadSerializer(
        read_only=True, many=True, source='schemes_result_holes'
    )
    model = SerializerMethodField()

    class Meta:
        model = ResultEquipment
        fields = [
            'id', 'model', 'x', 'y', 'z', 'rotate_y',
            'base_color', 'reflectivity', 'transparency', 'shininess',
            'holes', 'width', 'height', 'depth'
        ]

    def get_model(self, obj):
        request = self.context.get('request')
        if obj.model and request:
            return request.build_absolute_uri(obj.model.url)
        return None