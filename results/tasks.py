# results/tasks.py
from celery import shared_task
from django.db import transaction
import logging

from django.utils import timezone

from results.optimization import _perform_optimization

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def optimize_result_layout(self, result_id):
    """
    Асинхронная задача оптимизации размещения оборудования и трассировки труб.
    """
    from results.models import Result
    try:
        result = Result.objects.get(pk=result_id)
    except Result.DoesNotExist:
        logger.error(f"Result with id {result_id} not found")
        return

    # Устанавливаем флаг оптимизации
    result.is_optimizing = True
    result.save(update_fields=['is_optimizing'])

    try:
        # Основная логика оптимизации (будет описана далее)
        _perform_optimization(result)
    except Exception as e:
        logger.exception(f"Optimization failed for result {result_id}: {e}")
        # В случае ошибки снимаем флаг и, возможно, ретраим
        result.is_optimizing = False
        result.save(update_fields=['is_optimizing'])
        raise self.retry(exc=e, countdown=60)
    else:
        result.is_optimizing = False
        result.updated = timezone.now()
        result.save(update_fields=['is_optimizing', 'updated'])
