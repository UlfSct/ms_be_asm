from django.db.models import Model, ForeignKey, CASCADE

from equipments.models import EquipmentHole
from .scheme_equipment import SchemeEquipment


class SchemeEquipmentHole(Model):
    scheme_equipment = ForeignKey(SchemeEquipment, verbose_name='Оборудование схемы', on_delete=CASCADE, related_name='schemes_equipment_holes', null=False, blank=False)
    hole = ForeignKey(EquipmentHole, verbose_name='Отверстие', on_delete=CASCADE, related_name='schemes_equipment_holes', null=False, blank=False)

    class Meta:
        verbose_name = 'Отверстие оборудования схемы'
        verbose_name_plural = 'Отверстие оборудования схемы'

    def __str__(self):
        return self.name
