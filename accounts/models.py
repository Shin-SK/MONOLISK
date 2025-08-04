# accounts/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(
        'email address',
        blank=True,           # ← ここで任意化
        null=True,
        unique=False
    )
    store = models.ForeignKey(
        'billing.Store',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='users'
    )
    # 今後はここに “オーナー区分” とか “電話番号” とか足していくだけ
