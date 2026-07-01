from django.db.models import Model, ForeignKey, CASCADE, FloatField

from .result_equipment import ResultEquipment


class ResultEquipmentHole(Model):
    result_equipment = ForeignKey(ResultEquipment, verbose_name='Оборудование результата', on_delete=CASCADE, related_name='schemes_result_holes', null=False, blank=False)
    normal_x = FloatField(verbose_name='Вектор нормали по X', null=False, blank=True, default=0.0)
    normal_y = FloatField(verbose_name='Вектор нормали по Y', null=False, blank=True, default=0.0)
    normal_z = FloatField(verbose_name='Вектор нормали по Z', null=False, blank=True, default=0.0)
    offset_x = FloatField(verbose_name='Смещение по X', null=False, blank=True, default=0.0)
    offset_y = FloatField(verbose_name='Смещение по Y', null=False, blank=True, default=0.0)
    offset_z = FloatField(verbose_name='Смещение по Z', null=False, blank=True, default=0.0)

    class Meta:
        verbose_name = 'Отверстие оборудования результата'
        verbose_name_plural = 'Отверстие оборудования результата'

    def __str__(self):
        return self.name
