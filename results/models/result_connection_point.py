from django.db.models import Model, ForeignKey, CASCADE, FloatField, IntegerField
from django.core.validators import MinValueValidator

from .result_connection import ResultConnection


class ResultConnectionPoint(Model):
    connection = ForeignKey(ResultConnection, verbose_name='Соединение', on_delete=CASCADE, related_name='results_connection_points', null=False, blank=False)
    index = IntegerField(verbose_name='Индекс', validators=[MinValueValidator(0, message='Индекс не может быть меньше 0.')])
    x = FloatField(verbose_name='X', default=0.0)
    y = FloatField(verbose_name='X', default=0.0)
    z = FloatField(verbose_name='Z', default=0.0)

    class Meta:
        verbose_name = 'Точка соединения результата'
        verbose_name_plural = 'Точки соединения результата'

    def __str__(self):
        return self.name
