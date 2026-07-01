from django.db.models import Value, CharField, BooleanField, OuterRef, Case, When, Exists
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from model_constructor.models import Assembly, Part, AssemblyPart


class ProjectViewSet(ListModelMixin, GenericViewSet):
    def list(self, request, *args, **kwargs):
        return Response(list(
            Part.objects.annotate(
                type=Value('part', output_field=CharField()),
                can_delete=Case(
                    When(
                        ~Exists(AssemblyPart.objects.filter(part_id=OuterRef('pk'))),
                        then=Value(True, output_field=BooleanField())
                    ),
                    default=Value(False, output_field=BooleanField()),
                    output_field=BooleanField()
                )
            ).values(
                'id', 'name', 'created', 'updated', 'type', 'can_delete'
            ).union(
                Assembly.objects.annotate(
                    type=Value('assembly', output_field=CharField()),
                    can_delete=Value(True, output_field=BooleanField())
                ).values('id', 'name', 'created', 'updated', 'type', 'can_delete')
            ).order_by('-updated'))
        )
