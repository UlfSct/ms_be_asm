from rest_framework.serializers import ModelSerializer

from model_constructor.models import Plane


class CoordinateSystemPlaneSerializer(ModelSerializer):
    class Meta:
        model = Plane
        fields = [
            'id', 'name', 'normal_x', 'normal_y', 'normal_z', 'created', 'updated', 'is_hidden'
        ]


class PartPlaneSerializer(ModelSerializer):
    class Meta:
        model = Plane
        fields = [
            'id', 'name', 'normal_x', 'normal_y', 'normal_z',
            'offset_x', 'offset_y', 'offset_z', 'created', 'updated', 'is_hidden'
        ]


class AssemblyPlaneSerializer(PartPlaneSerializer):
    pass
