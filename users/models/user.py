from django.contrib.auth.models import AbstractUser
from django.db.models import CharField, EmailField, BooleanField


class User(AbstractUser):
    first_name = None
    last_name = None
    is_staff = BooleanField(default=False)
    is_superuser = BooleanField(default=False)
    groups = None
    user_permissions = None

    name = CharField(verbose_name='Имя', max_length=150)
    surname = CharField(verbose_name='Фамилия', max_length=150)
    lastname = CharField(verbose_name='Отчество', max_length=150, blank=True)
    email = EmailField(verbose_name='Email', unique=True)
    is_admin = BooleanField(verbose_name='Статус администратора', default=False)
    is_active = BooleanField(verbose_name='Статус активности', default=True)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.username} ({self.email})"

    @property
    def full_name(self):
        parts = [self.surname, self.name, self.lastname]
        return ' '.join(part for part in parts if part)