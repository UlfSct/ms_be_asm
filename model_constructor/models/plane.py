from django.db.models import Q, Model, TextField, DateTimeField, ForeignKey, CASCADE, FloatField, CheckConstraint, \
    BooleanField


class Plane(Model):
    name = TextField(verbose_name='Название')
    created = DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    updated = DateTimeField(verbose_name='Дата обновления', auto_now=True)
    normal_x = FloatField(verbose_name='Вектор нормали по X')
    normal_y = FloatField(verbose_name='Вектор нормали по Y')
    normal_z = FloatField(verbose_name='Вектор нормали по Z')
    offset_x = FloatField(verbose_name='Смещение по X', null=True, blank=True)
    offset_y = FloatField(verbose_name='Смещение по Y', null=True, blank=True)
    offset_z = FloatField(verbose_name='Смещение по Z', null=True, blank=True)
    is_hidden = BooleanField(verbose_name='Скрыто', default=False)

    part = ForeignKey(
        'Part',
        on_delete=CASCADE,
        null=True,
        blank=True,
        verbose_name='Деталь'
    )

    coordinate_system = ForeignKey(
        'CoordinateSystem',
        on_delete=CASCADE,
        null=True,
        blank=True,
        verbose_name='Система координат'
    )

    assembly = ForeignKey(
        'Assembly',
        on_delete=CASCADE,
        null=True,
        blank=True,
        verbose_name='Сборка'
    )

    class Meta:
        verbose_name = 'Плоскость'
        verbose_name_plural = 'Плоскости'
        constraints = [
            CheckConstraint(
                check=(
                        Q(part__isnull=False, coordinate_system__isnull=True, assembly__isnull=True) |
                        Q(part__isnull=True, coordinate_system__isnull=False, assembly__isnull=True) |
                        Q(part__isnull=True, coordinate_system__isnull=True, assembly__isnull=False)
                ),
                name='only_one_foreign_key'
            ),
            CheckConstraint(
                check=(
                        Q(coordinate_system__isnull=False) |
                        (Q(coordinate_system__isnull=True) &
                         Q(offset_x__isnull=False) &
                         Q(offset_y__isnull=False) &
                         Q(offset_z__isnull=False))
                ),
                name='offsets_required_without_cs'
            )
        ]