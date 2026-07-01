from django.db.models import Q
from django_filters import CharFilter
from django_filters.rest_framework import FilterSet


class SchemeFilter(FilterSet):
    search = CharFilter(method='filter_by_name_and_description', label='Поиск')

    def filter_by_name_and_description(self, queryset, name, value):
        if value:
            return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))
        return queryset