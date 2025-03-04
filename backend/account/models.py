from django.contrib.auth.models import AbstractUser
from django.db import models

class Store(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="店舗名")

    def __str__(self):
        return self.name

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', '管理者'),
        ('staff', 'スタッフ'),
        ('driver', 'ドライバー'),
        ('cast', 'キャスト'),
    )

    full_name = models.CharField(max_length=255, verbose_name="氏名", blank=True, null=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='staff')
    stores = models.ManyToManyField("Store", through="StoreUser", related_name="users")  # 🔥 `through=` を適用

    def save(self, *args, **kwargs):
        # スーパーユーザーなら role を自動で "admin" にする
        if self.is_superuser and self.role != "admin":
            self.role = "admin"
        super().save(*args, **kwargs)

    def get_store_nicknames(self):
        return ", ".join([f"{su.store.name}：{su.nickname}" for su in self.storeuser_set.all()])

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

class StoreUser(models.Model):  # 🔥 `CustomUser` の後に定義
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=255, verbose_name="ニックネーム")

    def __str__(self):
        return f"{self.store.name}：{self.nickname}"
