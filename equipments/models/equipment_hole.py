from django.db.models import Model, TextField, CASCADE, ForeignKey, FloatField

from equipments.models import Equipment


class EquipmentHole(Model):
    name = TextField(verbose_name='Название', unique=False)
    equipment = ForeignKey(Equipment, verbose_name='Оборудование', on_delete=CASCADE, related_name='holes', null=False, blank=False)
    normal_x = FloatField(verbose_name='Вектор нормали по X', null=False, blank=True, default=0.0)
    normal_y = FloatField(verbose_name='Вектор нормали по Y', null=False, blank=True, default=0.0)
    normal_z = FloatField(verbose_name='Вектор нормали по Z', null=False, blank=True, default=0.0)
    offset_x = FloatField(verbose_name='Смещение по X', null=False, blank=True, default=0.0)
    offset_y = FloatField(verbose_name='Смещение по Y', null=False, blank=True, default=0.0)
    offset_z = FloatField(verbose_name='Смещение по Z', null=False, blank=True, default=0.0)

    class Meta:
        verbose_name = 'Отверстие оборудования'
        verbose_name_plural = 'Отверстия оборудования'

    def __str__(self):
        return self.name
