from django.core.validators import FileExtensionValidator, MinValueValidator, RegexValidator, MaxValueValidator
from django.db.models import Model, ForeignKey, CASCADE, FloatField, FileField, CharField
from rest_framework.exceptions import ValidationError

from .result import Result


def validate_file_size_20(value):
    filesize = value.size
    if filesize > 20 * 1024 * 1024:
        raise ValidationError("Максимальный размер файла 20MB")


class ResultEquipment(Model):
    hex_validator = RegexValidator(
        regex='^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
        message='Введите цвет в формате HEX (#FFFFFF или #FFF)'
    )

    result = ForeignKey(Result, verbose_name='Схема', on_delete=CASCADE, related_name='result_equipments', null=False, blank=False)
    model = FileField(
        upload_to='result_models/',
        validators=[
            FileExtensionValidator(allowed_extensions=['fbx']),
            validate_file_size_20
        ]
    )
    width = FloatField(verbose_name='Ширина (X)', default=1.0)
    height = FloatField(verbose_name='Высота (Y)', default=1.0)
    depth = FloatField(verbose_name='Глубина (Z)', default=1.0)
    x = FloatField(verbose_name='X', default=0.0)
    y = FloatField(verbose_name='Y', default=0.0)
    z = FloatField(verbose_name='Z', default=0.0)
    rotate_y = FloatField(verbose_name='Поворот по оси Y', default=0.0)
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

    class Meta:
        verbose_name = 'Оборудование результата'
        verbose_name_plural = 'Оборудования результата'

    def __str__(self):
        return self.name
