from django.db.models import Model, ForeignKey, CASCADE, FloatField

from equipments.models import Equipment
from materials.models import Material
from .scheme import Scheme


class SchemeEquipment(Model):
    scheme = ForeignKey(Scheme, verbose_name='Схема', on_delete=CASCADE, related_name='schemes_equipments', null=False, blank=False)
    equipment = ForeignKey(Equipment, verbose_name='Оборудование', on_delete=CASCADE, related_name='schemes_equipments', null=False, blank=False)
    material = ForeignKey(Material, verbose_name='Материал', on_delete=CASCADE, related_name='schemes_equipments', null=False, blank=False)
    x = FloatField(verbose_name='X', default=0.0)
    z = FloatField(verbose_name='Z', default=0.0)

    class Meta:
        verbose_name = 'Оборудование схемы'
        verbose_name_plural = 'Оборудования схемы'

    def __str__(self):
        return self.name
