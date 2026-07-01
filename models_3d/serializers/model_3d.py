from rest_framework.fields import BooleanField, SerializerMethodField
from rest_framework.serializers import ModelSerializer
from rest_framework.exceptions import ValidationError

from models_3d.models import Model3D
from users.serializers import AdminUserRetrieveSerializer


class BaseModelSerializer(ModelSerializer):
    class Meta:
        model = Model3D
        fields = ['id', 'name', 'file']


class ModelListSerializer(ModelSerializer):
    can_delete = BooleanField(read_only=True)
    is_mine = BooleanField(read_only=True)

    class Meta:
        model = Model3D
        fields = ['id', 'name', 'file', 'share', 'can_delete', 'created', 'updated', 'is_mine', 'is_global']


class ModelDetailSerializer(ModelSerializer):
    can_delete = BooleanField(read_only=True)

    class Meta:
        model = Model3D
        fields = '__all__'


class ModelCreateSerializer(ModelSerializer):
    class Meta:
        model = Model3D
        fields = ['name', 'file', 'share', 'width', 'height', 'depth']

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.full_clean()
        return instance


class ModelUpdateSerializer(ModelCreateSerializer):
    def validate(self, attrs):
        if self.instance.is_global:
            raise ValidationError({'detail': 'Редактировать глобальные модели может только администратор системы.'})
        return attrs

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        instance.full_clean()
        return instance


class AdminModelListSerializer(ModelSerializer):
    can_delete = BooleanField(read_only=True)

    class Meta:
        model = Model3D
        fields = ['id', 'name', 'file', 'created', 'updated', 'can_delete']


class AdminModelDetailSerializer(ModelSerializer):
    can_delete = BooleanField(read_only=True)
    user = SerializerMethodField()

    def get_user(self, obj):
        return AdminUserRetrieveSerializer(obj.user).data

    class Meta:
        model = Model3D
        fields = '__all__'


class AdminModelCreateSerializer(ModelSerializer):
    class Meta:
        model = Model3D
        fields = ['name', 'file', 'description', 'width', 'height', 'depth']

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.full_clean()
        return instance


class AdminModelUpdateSerializer(AdminModelCreateSerializer):
    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        instance.full_clean()
        return instance
