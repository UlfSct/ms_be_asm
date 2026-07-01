from django.db.models import Model, TextField, DateTimeField


class Assembly(Model):
    name = TextField(verbose_name='Название', unique=True)
    description = TextField(verbose_name='Описание', blank=True, default='')
    created = DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    updated = DateTimeField(verbose_name='Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Сборка'
        verbose_name_plural = 'Сборки'

    def __str__(self):
        return self.name

    def create_default_coordinate_system_and_planes(self):
        from .coordinate_system import CoordinateSystem
        from .plane import Plane

        cs = CoordinateSystem.objects.create(
            name=f"Основная",
            offset_x=0.0,
            offset_y=0.0,
            offset_z=0.0,
            assembly=self
        )

        planes_data = [
            {
                'name': f"XY",
                'normal_x': 0.0,
                'normal_y': 0.0,
                'normal_z': 1.0,
            },
            {
                'name': f"XZ",
                'normal_x': 0.0,
                'normal_y': 1.0,
                'normal_z': 0.0,
            },
            {
                'name': f"YZ",
                'normal_x': 1.0,
                'normal_y': 0.0,
                'normal_z': 0.0,
            }
        ]

        for plane_data in planes_data:
            Plane.objects.create(
                **plane_data,
                coordinate_system=cs
            )
