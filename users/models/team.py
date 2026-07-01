from django.db.models import Model, CharField, DateTimeField, ForeignKey, CASCADE
from django.utils import timezone


class Team(Model):
    name = CharField(verbose_name='Название команды', max_length=255)
    created = DateTimeField(verbose_name='Дата создания', default=timezone.now)
    creator = ForeignKey('User', verbose_name='Создатель команды', on_delete=CASCADE, related_name='created_teams')

    class Meta:
        verbose_name = 'Команда'
        verbose_name_plural = 'Команды'
        ordering = ['-created']

    def __str__(self):
        return self.name
