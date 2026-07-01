from django.db.models import Q
from django_filters import CharFilter, NumberFilter
from django_filters.rest_framework import FilterSet

from equipments.models import EquipmentHole


class EquipmentTypeFilter(FilterSet):
    search = CharFilter(method='filter_by_name', label='Поиск')

    def filter_by_name(self, queryset, name, value):
        if value:
            return queryset.filter(Q(name__icontains=value))
        return queryset


class EquipmentFilter(FilterSet):
    search = CharFilter(method='filter_by_name_and_description', label='Поиск')

    def filter_by_name_and_description(self, queryset, name, value):
        if value:
            return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))
        return queryset


class EquipmentHoleFilter(FilterSet):
    equipment = NumberFilter(field_name='equipment__id', lookup_expr='exact')

    class Meta:
        model = EquipmentHole
        fields = ['equipment']
