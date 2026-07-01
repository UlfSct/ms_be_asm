from rest_framework.serializers import ModelSerializer

from schemes.models import SchemeConnectionPoint


class SchemeConnectionPointReadSerializer(ModelSerializer):
    class Meta:
        model = SchemeConnectionPoint
        fields = ['id', 'index', 'x', 'z']
