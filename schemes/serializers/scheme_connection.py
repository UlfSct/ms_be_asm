from rest_framework.serializers import ModelSerializer

from schemes.models import SchemeConnection
from schemes.serializers.scheme_connection_point import SchemeConnectionPointReadSerializer


class SchemeConnectionReadSerializer(ModelSerializer):
    points = SchemeConnectionPointReadSerializer(read_only=True, many=True, source='schemes_connection_points')

    class Meta:
        model = SchemeConnection
        fields = ['id', 'scheme_equipment_hole_start', 'scheme_equipment_hole_end', 'material', 'points', 'r']
