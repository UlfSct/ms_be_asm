from rest_framework.fields import BooleanField, SerializerMethodField
from rest_framework.serializers import ModelSerializer
from rest_framework.exceptions import ValidationError

from users.serializers import AdminUserRetrieveSerializer
from ..models import Material


class BaseMaterialSerializer(ModelSerializer):
    class Meta:
        model = Material
        fields = ['id', 'name']


class MaterialListSerializer(ModelSerializer):
    can_delete = BooleanField(read_only=True)
    is_mine = BooleanField(read_only=True)

    class Meta:
        model = Material
        fields = ['id', 'name', 'base_color', 'is_global', 'share', 'can_delete', 'created', 'updated', 'is_mine']


class MaterialDetailSerializer(ModelSerializer):
    can_delete = BooleanField(read_only=True)

    class Meta:
        model = Material
        fields = '__all__'


class MaterialCreateSerializer(ModelSerializer):
    class Meta:
        model = Material
        fields = ['name', 'description', 'base_color', 'reflectivity', 'transparency', 'shininess', 'share']

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.full_clean()
        return instance


class MaterialUpdateSerializer(MaterialCreateSerializer):
    def validate(self, attrs):
        if self.instance.is_global:
            raise ValidationError({'detail': 'Редактировать глобальные материалы может только администратор системы.'})
        return attrs

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        instance.full_clean()
        return instance


class AdminMaterialListSerializer(ModelSerializer):
    can_delete = BooleanField(read_only=True)

    class Meta:
        model = Material
        fields = ['id', 'name', 'base_color', 'can_delete', 'created', 'updated']


class AdminMaterialDetailSerializer(ModelSerializer):
    can_delete = BooleanField(read_only=True)
    user = SerializerMethodField()

    def get_user(self, obj):
        return AdminUserRetrieveSerializer(obj.user).data

    class Meta:
        model = Material
        fields = '__all__'


class AdminMaterialCreateSerializer(ModelSerializer):
    class Meta:
        model = Material
        fields = ['name', 'description', 'base_color', 'reflectivity', 'transparency', 'shininess']

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.full_clean()
        return instance


class AdminMaterialUpdateSerializer(AdminMaterialCreateSerializer):
    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        instance.full_clean()
        return instance
