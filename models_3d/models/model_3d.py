from django.core.validators import FileExtensionValidator, ValidationError
from django.db.models import Model, TextField, FileField, DateTimeField, BooleanField, ForeignKey, CASCADE, FloatField

from users.models import User


def validate_file_size_20(value):
    filesize = value.size
    if filesize > 20 * 1024 * 1024:
        raise ValidationError("Максимальный размер файла 20MB")


class Model3D(Model):
    name = TextField(verbose_name='Название', unique=True)
    file = FileField(
        upload_to='models/',
        validators=[
            FileExtensionValidator(allowed_extensions=['fbx']),
            validate_file_size_20
        ]
    )
    description = TextField(verbose_name='Описание', blank=True, default='')
    created = DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    updated = DateTimeField(verbose_name='Дата обновления', auto_now=True)
    user = ForeignKey(User, verbose_name='Пользователь', on_delete=CASCADE, related_name='models', null=False, blank=False)
    is_global = BooleanField(verbose_name='Глобальный материал', default=False)
    share = BooleanField(verbose_name='Поделиться с командой', default=False)
    width = FloatField(verbose_name='Ширина (X)', default=1.0, help_text='Размер по оси X в метрах')
    height = FloatField(verbose_name='Высота (Y)', default=1.0, help_text='Размер по оси Y в метрах')
    depth = FloatField(verbose_name='Глубина (Z)', default=1.0, help_text='Размер по оси Z в метрах')

    class Meta:
        verbose_name = 'Модель'
        verbose_name_plural = 'Модели'

    def __str__(self):
        return self.name