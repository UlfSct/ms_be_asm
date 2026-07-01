from django.db.models import Model, TextField, DateTimeField, BooleanField, ForeignKey, CASCADE, UniqueConstraint

from equipments.models import EquipmentType
from models_3d.models import Model3D
from users.models import User


class Equipment(Model):
    name = TextField(verbose_name='Название', unique=True)
    description = TextField(verbose_name='Описание', blank=True, default='')
    created = DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    updated = DateTimeField(verbose_name='Дата обновления', auto_now=True)
    user = ForeignKey(User, verbose_name='Пользователь', on_delete=CASCADE, related_name='equipments', null=False, blank=False)
    is_global = BooleanField(verbose_name='Глобальный материал', default=False)
    share = BooleanField(verbose_name='Поделиться с командой', default=False)
    model = ForeignKey(Model3D, verbose_name='Модель', on_delete=CASCADE, related_name='equipments', null=False, blank=False)
    type = ForeignKey(EquipmentType, verbose_name='Тип', on_delete=CASCADE, related_name='equipments', null=False, blank=False)

    class Meta:
        verbose_name = 'Модель'
        verbose_name_plural = 'Модели'

    def __str__(self):
        return self.name