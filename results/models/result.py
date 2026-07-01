from django.db.models import Model, DateTimeField, ForeignKey, CASCADE, TextField, BooleanField

from users.models import User


class Result(Model):
    name = TextField(verbose_name='Название')
    created = DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    updated = DateTimeField(verbose_name='Дата обновления', auto_now=True)
    user = ForeignKey(User, verbose_name='Пользователь', on_delete=CASCADE, related_name='results', null=False, blank=False)
    is_optimizing = BooleanField(verbose_name='В процессе оптимизации', default=False)

    class Meta:
        verbose_name = 'Результат'
        verbose_name_plural = 'Результаты'

    def __str__(self):
        return self.name
