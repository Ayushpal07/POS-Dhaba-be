from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        WAITER = 'WAITER', 'Waiter'

    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users',
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.WAITER)

    def __str__(self):
        return self.username
