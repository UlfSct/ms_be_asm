from django.core.validators import FileExtensionValidator, ValidationError
from django.db.models import Model, TextField, FileField, BooleanField


def validate_file_size(value):
    filesize = value.size
    if filesize > 5 * 1024 * 1024:
        raise ValidationError("Максимальный размер файла 5MB")


class EquipmentType(Model):
    name = TextField(verbose_name='Название', unique=True)
    file = FileField(
        upload_to='equipment_types/',
        validators=[
            FileExtensionValidator(allowed_extensions=['svg']),
            validate_file_size
        ]
    )
    is_active = BooleanField(verbose_name='Активность', default=True)

    class Meta:
        verbose_name = 'Тип оборудования'
        verbose_name_plural = 'Типы оборудования'

    def __str__(self):
        return self.name
