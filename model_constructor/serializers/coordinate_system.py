from rest_framework.serializers import ModelSerializer


class CoordinateSystemSerializer(ModelSerializer):
    class Meta:
        from model_constructor.models import CoordinateSystem
        model = CoordinateSystem
        fields = [
            'id', 'name', 'offset_x', 'offset_y', 'offset_z',
            'created', 'updated', 'is_hidden'
        ]

    def get_fields(self):
        fields = super().get_fields()

        from .plane import CoordinateSystemPlaneSerializer

        fields['planes'] = CoordinateSystemPlaneSerializer(
            many=True,
            read_only=True,
            source='plane_set'
        )

        return fields
