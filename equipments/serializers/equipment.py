from rest_framework.fields import BooleanField, SerializerMethodField
from rest_framework.serializers import ModelSerializer
from rest_framework.exceptions import ValidationError

from models_3d.serializers import BaseModelSerializer
from users.serializers import AdminUserRetrieveSerializer
from .equipment_hole import DetailEquipmentHoleSerializer, BaseEquipmentHoleSerializer
from .equipment_type import BaseEquipmentTypeSerializer
from ..models import Equipment


class BaseEquipmentSerializer(ModelSerializer):
    model = SerializerMethodField()
    type = SerializerMethodField()
    holes = SerializerMethodField()

    class Meta:
        model = Equipment
        fields = ['id', 'name', 'type', 'model', 'holes']

    def get_model(self, obj):
        return BaseModelSerializer(obj.model).data

    def get_type(self, obj):
        return BaseEquipmentTypeSerializer(obj.type).data

    def get_holes(self, obj):
        return BaseEquipmentHoleSerializer(obj.holes, many=True).data


class EquipmentListSerializer(ModelSerializer):
    can_delete = BooleanField(read_only=True)
    is_mine = BooleanField(read_only=True)
    model = SerializerMethodField()
    type = SerializerMethodField()

    class Meta:
        model = Equipment
        fields = ['id', 'name', 'model', 'type', 'share', 'can_delete', 'created', 'updated', 'is_mine', 'is_global']

    def get_model(self, obj):
        return BaseModelSerializer(obj.model).data

    def get_type(self, obj):
        return BaseEquipmentTypeSerializer(obj.type).data


class EquipmentDetailSerializer(ModelSerializer):
    can_delete = BooleanField(read_only=True)
    model = SerializerMethodField()
    type = SerializerMethodField()
    holes = SerializerMethodField()

    class Meta:
        model = Equipment
        fields = '__all__'

    def get_model(self, obj):
        return BaseModelSerializer(obj.model).data

    def get_type(self, obj):
        return BaseEquipmentTypeSerializer(obj.type).data

    def get_holes(self, obj):
        return DetailEquipmentHoleSerializer(obj.holes, many=True).data


class EquipmentCreateSerializer(ModelSerializer):
    class Meta:
        model = Equipment
        fields = ['name', 'description', 'model', 'type', 'share']

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.full_clean()
        return instance


class EquipmentUpdateSerializer(ModelSerializer):
    class Meta:
        model = Equipment
        fields = ['name', 'description', 'share']

    def validate(self, attrs):
        if self.instance.is_global:
            raise ValidationError({'detail': 'Редактировать глобальное оборудование может только администратор системы.'})
        return attrs

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        instance.full_clean()
        return instance


class AdminEquipmentListSerializer(ModelSerializer):
    can_delete = BooleanField(read_only=True)
    model = SerializerMethodField()
    type = SerializerMethodField()

    class Meta:
        model = Equipment
        fields = ['id', 'name', 'model', 'type', 'updated', 'created', 'can_delete']

    def get_model(self, obj):
        return BaseModelSerializer(obj.model).data

    def get_type(self, obj):
        return BaseEquipmentTypeSerializer(obj.type).data


class AdminEquipmentDetailSerializer(ModelSerializer):
    can_delete = BooleanField(read_only=True)
    user = SerializerMethodField()
    model = SerializerMethodField()
    type = SerializerMethodField()
    holes = SerializerMethodField()

    def get_user(self, obj):
        return AdminUserRetrieveSerializer(obj.user).data

    def get_model(self, obj):
        return BaseModelSerializer(obj.model).data

    def get_type(self, obj):
        return BaseEquipmentTypeSerializer(obj.type).data

    def get_holes(self, obj):
        return DetailEquipmentHoleSerializer(obj.holes, many=True).data

    class Meta:
        model = Equipment
        fields = '__all__'


class AdminEquipmentCreateSerializer(ModelSerializer):
    class Meta:
        model = Equipment
        fields = ['name', 'description', 'model', 'type']

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.full_clean()
        return instance


class AdminEquipmentUpdateSerializer(ModelSerializer):
    class Meta:
        model = Equipment
        fields = ['name', 'description']

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        instance.full_clean()
        return instance
