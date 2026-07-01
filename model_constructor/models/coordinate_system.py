from django.db.models import Model, TextField, DateTimeField, ForeignKey, CASCADE, FloatField, CheckConstraint, Q, \
    BooleanField


class CoordinateSystem(Model):
    name = TextField(verbose_name='Название')
    created = DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    updated = DateTimeField(verbose_name='Дата обновления', auto_now=True)
    offset_x = FloatField(verbose_name='Координата X')
    offset_y = FloatField(verbose_name='Координата Y')
    offset_z = FloatField(verbose_name='Координата Z')
    is_hidden = BooleanField(verbose_name='Скрыто', default=False)

    part = ForeignKey(
        'Part',
        on_delete=CASCADE,
        null=True,
        blank=True,
        verbose_name='Деталь'
    )

    assembly = ForeignKey(
        'Assembly',
        on_delete=CASCADE,
        null=True,
        blank=True,
        verbose_name='Сборка'
    )

    class Meta:
        verbose_name = 'Система координат'
        verbose_name_plural = 'Системы координат'
        constraints = [
            CheckConstraint(
                check=(
                        Q(part__isnull=False, assembly__isnull=True) |
                        Q(part__isnull=True, assembly__isnull=False)
                ),
                name='only_one_foreign_key_cs'
            ),
        ]

    def __str__(self):
        return f"{self.name}"
