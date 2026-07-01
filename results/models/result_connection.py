from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db.models import Model, ForeignKey, CASCADE, CharField, FloatField

from .result_equipment_hole import ResultEquipmentHole


class ResultConnection(Model):
    hex_validator = RegexValidator(
        regex='^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
        message='Введите цвет в формате HEX (#FFFFFF или #FFF)'
    )

    result_equipment_hole_start = ForeignKey(ResultEquipmentHole, verbose_name='Первое отверстие результата', on_delete=CASCADE, related_name='results_connections_starts', null=False, blank=False)
    result_equipment_hole_end = ForeignKey(ResultEquipmentHole, verbose_name='Второе отверстие результата', on_delete=CASCADE, related_name='results_connections_ends', null=False, blank=False)
    base_color = CharField(verbose_name='Базовый цвет (HEX)', max_length=7, validators=[hex_validator])
    reflectivity = FloatField(
        verbose_name='Отражаемость',
        validators=[
            MinValueValidator(0.0, message='Отражаемость не может быть меньше 0.'),
            MaxValueValidator(1.0, message='Отражаемость не может превышать 1.')
        ]
    )
    transparency = FloatField(
        verbose_name='Прозрачность',
        validators=[
            MinValueValidator(0.0, message='Прозрачность не может быть меньше 0.'),
            MaxValueValidator(1.0, message='Прозрачность не может превышать 1.')
        ]
    )
    shininess = FloatField(
        verbose_name='Блестящесть',
        validators=[
            MinValueValidator(0.0, message='Блестящесть не может быть меньше 0.'),
            MaxValueValidator(1.0, message='Блестящесть не может превышать 1.')
        ]
    )
    r = FloatField(verbose_name='Радиус', null=False, blank=False, default=20.0)

    class Meta:
        verbose_name = 'Соединение результата'
        verbose_name_plural = 'Соединения результата'

    def __str__(self):
        return self.name
