from django.db.models import Model, BooleanField, DateTimeField, ForeignKey, CASCADE


class TeamUser(Model):
    team = ForeignKey( 'Team', verbose_name='Команда', on_delete=CASCADE, related_name='members')
    user = ForeignKey('User', verbose_name='Пользователь', on_delete=CASCADE, related_name='team_memberships')
    is_admin = BooleanField(verbose_name='Администратор команды', default=False)
    joined = DateTimeField(verbose_name='Дата присоединения', auto_now_add=True)
    is_approved = BooleanField(verbose_name='Одобрено вступление', default=None, null=True)

    class Meta:
        verbose_name = 'Участник команды'
        verbose_name_plural = 'Участники команд'

        unique_together = ['team', 'user']
        ordering = ['-joined']

    def __str__(self):
        admin_status = " (админ)" if self.is_admin else ""
        return f"{self.user.username} в {self.team.name}{admin_status}"
