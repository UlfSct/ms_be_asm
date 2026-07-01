from django.db.models import Q
from django_filters import CharFilter
from django_filters.rest_framework import FilterSet


class MaterialFilter(FilterSet):
    search = CharFilter(method='modelfilter_by_name_and_description', label='Поиск')

    def modelfilter_by_name_and_description(self, queryset, name, value):
        if value:
            return queryset.filter(
                Q(name__icontains=value) | Q(description__icontains=value)
            )
        return queryset
