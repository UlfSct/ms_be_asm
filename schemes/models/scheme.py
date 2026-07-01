from django.db.models import Model, TextField, DateTimeField, ForeignKey, CASCADE

from users.models import User


class Scheme(Model):
    name = TextField(verbose_name='Название', unique=True)
    description = TextField(verbose_name='Описание', blank=True, default='')
    created = DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    updated = DateTimeField(verbose_name='Дата обновления', auto_now=True)
    user = ForeignKey(User, verbose_name='Пользователь', on_delete=CASCADE, related_name='schemes', null=False, blank=False)

    class Meta:
        verbose_name = 'Схема'
        verbose_name_plural = 'Схемы'

    def __str__(self):
        return self.name
