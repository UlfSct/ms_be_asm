from django.db.models import Model, ForeignKey, PROTECT, FloatField, TextField, DateTimeField, UniqueConstraint


class AssemblyPart(Model):
    name = TextField(verbose_name='Название детали в сборке')
    created = DateTimeField(verbose_name='Дата добавления', auto_now_add=True)
    updated = DateTimeField(verbose_name='Дата обновления', auto_now=True)
    offset_x = FloatField(verbose_name='Смещение X', default=0.0)
    offset_y = FloatField(verbose_name='Смещение Y', default=0.0)
    offset_z = FloatField(verbose_name='Смещение Z', default=0.0)
    rotation_x = FloatField(verbose_name='Поворот X', default=0.0)
    rotation_y = FloatField(verbose_name='Поворот Y', default=0.0)
    rotation_z = FloatField(verbose_name='Поворот Z', default=0.0)

    assembly = ForeignKey(
        'Assembly',
        on_delete=PROTECT,
        verbose_name='Сборка'
    )
    part = ForeignKey(
        'Part',
        on_delete=PROTECT,
        verbose_name='Деталь'
    )

    class Meta:
        verbose_name = 'Деталь в сборке'
        verbose_name_plural = 'Детали в сборках'
        constraints = [
            UniqueConstraint(
                fields=['assembly', 'name'],
                name='unique_assembly_part_name'
            )
        ]

    def __str__(self):
        return f'{self.part.name} в {self.assembly.name}'
