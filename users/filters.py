from functools import reduce
from operator import or_

from django.db.models import Q
from django_filters import CharFilter
from django_filters.rest_framework import FilterSet


class UserFilter(FilterSet):
    search = CharFilter(method='filter_by_full_name_or_username_or_email')

    def filter_by_full_name_or_username_or_email(self, queryset, name, value):
        if not value:
            return queryset

        search_terms = value.split()

        if not search_terms:
            return queryset

        fields = ['name', 'surname', 'lastname', 'username', 'email']

        conditions = [
            Q(**{f"{field}__icontains": term})
            for term in search_terms
            for field in fields
        ]

        if conditions:
            combined_q = reduce(or_, conditions)
            queryset = queryset.filter(combined_q)

        return queryset.distinct().order_by('-id')

