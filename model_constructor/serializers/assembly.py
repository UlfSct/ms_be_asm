from rest_framework.fields import SerializerMethodField, ListField, BooleanField
from rest_framework.serializers import ModelSerializer

from ..models import Assembly


class AssemblyDetailSerializer(ModelSerializer):
    parts = ListField(read_only=True)
    type = SerializerMethodField()
    can_delete = BooleanField(read_only=True)

    class Meta:
        model = Assembly
        fields = '__all__'

    def get_type(self, obj):
        return 'assembly'


class AssemblyCreateSerializer(ModelSerializer):
    class Meta:
        model = Assembly
        fields = '__all__'
        read_only_fields = ['id', 'created', 'updated']

    def create(self, validated_data):
        assembly = super().create(validated_data)

        try:
            assembly.create_default_coordinate_system_and_planes()
        except Exception as e:
            assembly.delete()
            raise e
        return assembly


class AssemblyUpdateSerializer(ModelSerializer):
    class Meta:
        model = Assembly
        fields = '__all__'
        read_only_fields = ['id', 'created', 'updated']


class AssemblyFullInfoSerializer(ModelSerializer):
    from .coordinate_system import CoordinateSystemSerializer
    from .plane import AssemblyPlaneSerializer

    coordinate_systems = CoordinateSystemSerializer(
        many=True,
        read_only=True,
        source='coordinatesystem_set'
    )

    planes = AssemblyPlaneSerializer(
        many=True,
        read_only=True,
        source='plane_set'
    )

    class Meta:
        model = Assembly
        fields = [
            'id', 'name', 'description', 'created', 'updated', 'coordinate_systems', 'planes',
        ]