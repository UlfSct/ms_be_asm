from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.db.models import Model, TextField, DateTimeField, FloatField, CharField, BooleanField, ForeignKey, CASCADE

from users.models import User


class Material(Model):
    hex_validator = RegexValidator(
        regex='^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
        message='Введите цвет в формате HEX (#FFFFFF или #FFF)'
    )

    name = TextField(verbose_name='Название', unique=True)
    description = TextField(verbose_name='Описание', blank=True, default='')
    created = DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    updated = DateTimeField(verbose_name='Дата обновления', auto_now=True)
    user = ForeignKey(User, verbose_name='Пользователь', on_delete=CASCADE, related_name='materials', null=False, blank=False)
    is_global = BooleanField(verbose_name='Глобальный материал', default=False)
    share = BooleanField(verbose_name='Поделиться с командой', default=False)

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
        verbose_name = 'Материал'
        verbose_name_plural = 'Материалы'

    def __str__(self):
        return self.name
