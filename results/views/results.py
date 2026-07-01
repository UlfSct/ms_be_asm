from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status

from be_asm_3d.permissions import IsAuthenticated
from be_asm_3d.utils import DefaultPagination
from results.models import Result
from results.serializers import BaseResultSerializer, ResultFullSerializer
from ..tasks import optimize_result_layout


class ResultViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination
    queryset = Result.objects.all()
    serializer_class = BaseResultSerializer

    http_method_names = ['get', 'delete', 'head', 'options', 'post']

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='full', url_name='full')
    def full(self, request, pk=None):
        result = self.get_object()
        serializer = ResultFullSerializer(result, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='optimize', url_name='optimize')
    def optimize(self, request, pk=None):
        result = self.get_object()
        if result.is_optimizing:
            return Response(
                {'detail': 'Оптимизация уже выполняется для этого результата.'},
                status=status.HTTP_409_CONFLICT
            )
        # Запускаем Celery задачу
        task = optimize_result_layout.delay(result.pk)
        return Response(
            {'detail': 'Оптимизация запущена.', 'task_id': task.id},
            status=status.HTTP_202_ACCEPTED
        )
