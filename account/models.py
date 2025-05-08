from django.db import models
from django.contrib.auth.models import AbstractUser

class Store(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="店舗名")
    def __str__(self):
        return self.name

class Rank(models.Model):
    """
    キャストのランク。各時間帯の基本料金や星ごとの加算額を管理
    """
    name = models.CharField(max_length=50, unique=True)  # "Luxury", "Black", "Platinum" など
    
    price_60 = models.IntegerField(default=0)
    price_75 = models.IntegerField(default=0)
    price_90 = models.IntegerField(default=0)
    price_120 = models.IntegerField(default=0)
    price_150 = models.IntegerField(default=0)
    price_180 = models.IntegerField(default=0)
    
    price_extension_30 = models.IntegerField(default=0)
    
    plus_per_star = models.IntegerField(default=1000)
    
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
    stores = models.ManyToManyField("Store", through="StoreUser", related_name="users")  

    def save(self, *args, **kwargs):
        # スーパーユーザーなら role を自動で "admin" にする
        if self.is_superuser and self.role != "admin":
            self.role = "admin"
        super().save(*args, **kwargs)

    def get_store_nicknames(self):
        return ", ".join([f"{su.store.name}：{su.nickname}" for su in self.storeuser_set.all()])

    def __str__(self):
        return self.full_name or self.username




class StoreUser(models.Model):
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE,
        verbose_name="キャスト"  # ← 表示ラベルを変更
    )
    store = models.ForeignKey(
        Store, 
        on_delete=models.CASCADE,
        verbose_name="店舗"
    )
    rank = models.ForeignKey(
        Rank, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="ランク"
    )
    star_count = models.IntegerField(default=0, verbose_name="☆数")
    nickname = models.CharField(
        max_length=255,
        verbose_name="ニックネーム",
        blank=True, 
        null=True
    )
    cast_photo = models.ImageField(
        null=True, 
        blank=True,
        verbose_name="キャスト写真"
    )

    def __str__(self):
        info = f"{self.user} / {self.store.name}"
        if self.rank:
            info += f" / Rank: {self.rank.name}, ☆ x {self.star_count}"
        return info
