from rest_framework.serializers import ModelSerializer

from results.models import ResultConnectionPoint


class ResultConnectionPointReadSerializer(ModelSerializer):
    class Meta:
        model = ResultConnectionPoint
        fields = ['id', 'index', 'x', 'y', 'z']