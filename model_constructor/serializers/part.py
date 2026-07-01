from rest_framework.fields import SerializerMethodField, BooleanField
from rest_framework.serializers import ModelSerializer

from materials.serializers import BaseMaterialSerializer
from ..models import Part


class PartDetailSerializer(ModelSerializer):
    material = BaseMaterialSerializer(read_only=True)
    type = SerializerMethodField()
    can_delete = BooleanField(read_only=True)

    class Meta:
        model = Part
        fields = '__all__'

    def get_type(self, obj):
        return 'part'


class PartCreateSerializer(ModelSerializer):
    class Meta:
        model = Part
        fields = '__all__'
        read_only_fields = ['id', 'created', 'updated']

    def create(self, validated_data):
        part = super().create(validated_data)

        try:
            part.create_default_coordinate_system_and_planes()
        except Exception as e:
            part.delete()
            raise e
        return part


class PartUpdateSerializer(ModelSerializer):
    class Meta:
        model = Part
        fields = '__all__'
        read_only_fields = ['id', 'created', 'updated']


class PartFullInfoSerializer(ModelSerializer):
    from materials.serializers.material import MaterialDetailSerializer
    from .coordinate_system import CoordinateSystemSerializer
    from .plane import PartPlaneSerializer
    material = MaterialDetailSerializer(read_only=True)

    coordinate_systems = CoordinateSystemSerializer(
        many=True,
        read_only=True,
        source='coordinatesystem_set'
    )

    planes = PartPlaneSerializer(
        many=True,
        read_only=True,
        source='plane_set'
    )

    class Meta:
        model = Part
        fields = [
            'id', 'name', 'description', 'material', 'created', 'updated', 'coordinate_systems', 'planes',
        ]
