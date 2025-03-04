from django.db import models
from account.models import CustomUser, Store, StoreUser

class Course(models.Model):
    name = models.CharField(max_length=255, verbose_name="コース名")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="料金")

    def __str__(self):
        return self.name

class Menu(models.Model):
    name = models.CharField(max_length=255, verbose_name="メニュー名")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="料金")

    def __str__(self):
        return self.name

class Discount(models.Model):
    """割引を管理するモデル"""
    name = models.CharField(max_length=255, verbose_name="割引名")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="割引額")

    def __str__(self):
        return f"{self.name}（-{self.amount}円）"


class Reservation(models.Model):
    """ 予約のメインモデル """

    # メイン情報
    customer_name = models.CharField(max_length=255, verbose_name="お客様の名前")
    start_time = models.DateTimeField(verbose_name="予約開始時刻", null=True, blank=True)

    # コースやメニュー、割引
    course = models.ForeignKey("Course", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="コース")
    menus = models.ManyToManyField("Menu", blank=True, verbose_name="メニュー")
    discounts = models.ManyToManyField("Discount", blank=True, verbose_name="適用割引")

    # 店舗、キャスト、ドライバー
    store = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="店舗")
    cast = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations_as_cast')
    driver = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations_as_driver')
    store_user = models.ForeignKey(StoreUser, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="店舗×キャスト")

    # 受取金 (キャスト、ドライバー、店舗) 
    cast_received = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    driver_received = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    store_received = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # 会員区分
    MEMBERSHIP_CHOICES = [
        ("new", "新規"),
        ("general", "一般会員"),
        ("member", "本会員"),
    ]
    membership_type = models.CharField(
        max_length=50,
        choices=MEMBERSHIP_CHOICES,
        default="general",
        verbose_name="会員種別"
    )

    # 予約時間や料金
    time_minutes = models.IntegerField(verbose_name="予約時間（分）", null=True, blank=True)
    reservation_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="予約金")

    # 追加オプション
    enrollment_fee = models.BooleanField(default=False, verbose_name="入会金あり")
    enrollment_fee_discounted = models.BooleanField(default=True, verbose_name="入会金0円割引")
    photo_nomination_fee = models.BooleanField(default=False, verbose_name="写真指名あり")
    photo_nomination_fee_discounted = models.BooleanField(default=True, verbose_name="写真指名0円割引")
    regular_nomination_fee = models.BooleanField(default=False, verbose_name="本指名あり")
    regular_nomination_fee_discounted = models.BooleanField(default=True, verbose_name="本指名割引")

    def __str__(self):
        return f"[{self.id}] {self.customer_name} - {self.start_time} "

    def save(self, *args, **kwargs):
        """
        ここでサーバー側の計算をしてもいいし、
        フロントだけで計算して 'reservation_amount' を送ってもいい
        """
        # 例: store_userがあれば store/cast を同期
        if self.store_user:
            self.store = self.store_user.store
            self.cast = self.store_user.user
        # ここで計算ロジックを書くなら書く
        super().save(*args, **kwargs)


class StorePricing(models.Model):
    """
    各店舗の料金テーブル（例）
    """
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="pricings")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="対象コース")
    time_minutes = models.IntegerField(verbose_name="時間（分）")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="料金")

    def __str__(self):
        return f"{self.store.name} - {self.course.name} - {self.time_minutes}分：{self.price}円"
