from django.db.models import Model, ForeignKey, CASCADE, FloatField, IntegerField
from django.core.validators import RegexValidator, MinValueValidator

from .scheme_connection import SchemeConnection


class SchemeConnectionPoint(Model):
    connection = ForeignKey(SchemeConnection, verbose_name='Соединение', on_delete=CASCADE, related_name='schemes_connection_points', null=False, blank=False)
    index = IntegerField(verbose_name='Индекс', validators=[MinValueValidator(0, message='Индекс не может быть меньше 0.')])
    x = FloatField(verbose_name='X', default=0.0)
    z = FloatField(verbose_name='Z', default=0.0)

    class Meta:
        verbose_name = 'Точка соединения схемы'
        verbose_name_plural = 'Точки соединения схемы'

    def __str__(self):
        return self.name
