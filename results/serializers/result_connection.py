from rest_framework.serializers import ModelSerializer

from results.models import ResultConnection
from results.serializers.result_connection_point import ResultConnectionPointReadSerializer


class ResultConnectionReadSerializer(ModelSerializer):
    points = ResultConnectionPointReadSerializer(
        read_only=True, many=True, source='results_connection_points'
    )

    class Meta:
        model = ResultConnection
        fields = [
            'id', 'result_equipment_hole_start', 'result_equipment_hole_end',
            'base_color', 'reflectivity', 'transparency', 'shininess',
            'points', 'r'
        ]