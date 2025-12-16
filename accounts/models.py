# accounts/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.db.models import Q

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



class StoreRole(models.TextChoices):
    OWNER   = 'owner',   'Owner'     # 複数店舗の閲覧（PL/詳細系Read）
    MANAGER = 'manager', 'Manager'   # 自店フル操作
    STAFF   = 'staff',   'Staff'     # 実務操作（伝票/注文/会計/締め）
    CAST    = 'cast',    'Cast'      # キャスト（限定機能）
    DRIVER  = 'driver',  'Driver'    # 既存互換（必要なら）

class StoreMembership(models.Model):
    user  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    store = models.ForeignKey('billing.Store', on_delete=models.CASCADE, related_name='memberships')
    role  = models.CharField(max_length=20, choices=StoreRole.choices)
    is_primary = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'store'],
                name='uniq_storemembership_user_store',
            ),
            models.UniqueConstraint(
                fields=['user'],
                condition=Q(is_primary=True),
                name='unique_primary_membership_per_user',
            ),
        ]

    def __str__(self):
        return f'{self.user_id}:{self.store_id}:{self.role}'
