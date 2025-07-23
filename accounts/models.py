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
    # 今後はここに “オーナー区分” とか “電話番号” とか足していくだけ
