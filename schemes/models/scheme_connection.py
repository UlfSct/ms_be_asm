from django.db.models import Model, ForeignKey, CASCADE, FloatField

from materials.models import Material
from .scheme_equipment_hole import SchemeEquipmentHole


class SchemeConnection(Model):
    scheme_equipment_hole_start = ForeignKey(SchemeEquipmentHole, verbose_name='Первое отверстие соединения', on_delete=CASCADE, related_name='schemes_connections_starts', null=False, blank=False)
    scheme_equipment_hole_end = ForeignKey(SchemeEquipmentHole, verbose_name='Второе отверстие соединения', on_delete=CASCADE, related_name='schemes_connections_ends', null=False, blank=False)
    material = ForeignKey(Material, verbose_name='Материал', on_delete=CASCADE, related_name='schemes_connections', null=False, blank=False)
    r = FloatField(verbose_name='Радиус', null=False, blank=False, default=20.0)

    class Meta:
        verbose_name = 'Соединение схемы'
        verbose_name_plural = 'Соединения схемы'

    def __str__(self):
        return self.name
