from django.db import models
from account.models import CustomUser, Store  

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
    customer_name = models.CharField(max_length=255, verbose_name="お客様の名前")
    start_time = models.DateTimeField(verbose_name="予約開始時刻")
    course = models.ForeignKey("Course", on_delete=models.CASCADE, verbose_name="コース", null=True, blank=True)
    menus = models.ManyToManyField("Menu", blank=True, verbose_name="メニュー")
    store = models.ForeignKey(Store, on_delete=models.CASCADE, verbose_name="店舗", null=True, blank=True)
    cast = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, verbose_name="キャスト", null=True, blank=True, related_name='reservations_as_cast')
    driver = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, verbose_name="ドライバー", null=True, blank=True, related_name='reservations_as_driver')
    cast_received = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    driver_received = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    store_received = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    MEMBERSHIP_CHOICES = [
        ("new", "新規"),
        ("general", "一般会員"),
        ("member", "本会員"),
    ]
    membership_type = models.CharField(
        max_length=50,
        choices=MEMBERSHIP_CHOICES,
        default="general",
        verbose_name="会員種別",
    )

    time_minutes = models.IntegerField(verbose_name="予約時間（分）", null=True, blank=True)
    reservation_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="予約金", null=True, blank=True)

    # 🔥 割引の追加（予約に複数の割引を適用できる）
    discounts = models.ManyToManyField("Discount", blank=True, verbose_name="適用割引")

    # 🔥 追加オプション
    enrollment_fee = models.BooleanField(default=False, verbose_name="入会金あり")
    enrollment_fee_discounted = models.BooleanField(default=True, verbose_name="入会金0円（期間限定）")

    photo_nomination_fee = models.BooleanField(default=False, verbose_name="写真指名あり")
    photo_nomination_fee_discounted = models.BooleanField(default=True, verbose_name="写真指名0円（期間限定）")

    regular_nomination_fee = models.BooleanField(default=False, verbose_name="本指名あり")
    regular_nomination_fee_discounted = models.BooleanField(default=True, verbose_name="本指名2000円（期間限定）")

    def save(self, *args, **kwargs):
        total_price = 0

        # コース料金を取得
        if self.course and self.store and self.time_minutes:
            pricing = StorePricing.objects.filter(
                store=self.store,
                course=self.course,
                time_minutes=self.time_minutes
            ).first()
            if pricing:
                total_price += pricing.price

        # メニュー料金を合計
        total_price += sum(menu.price for menu in self.menus.all())

        # 🔥 追加オプションの料金を加算
        if self.enrollment_fee:
            total_price += 5000 if not self.enrollment_fee_discounted else 0

        if self.photo_nomination_fee:
            total_price += 2000 if not self.photo_nomination_fee_discounted else 0

        if self.regular_nomination_fee:
            total_price += 3000 if not self.regular_nomination_fee_discounted else 2000

        # 🔥 割引を適用（合計金額から割引を減算）
        total_discount = sum(discount.amount for discount in self.discounts.all())
        total_price -= total_discount

        # 最終的な予約金を設定
        self.reservation_amount = max(0, total_price)  # 🔥 予約金がマイナスにならないように調整

        super().save(*args, **kwargs)

class StorePricing(models.Model):
    """
    各店舗の料金テーブル（会員種別は削除）
    """
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="pricings")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="対象コース")
    time_minutes = models.IntegerField(verbose_name="時間（分）")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="料金")

    def __str__(self):
        return f"{self.store.name} - {self.course.name} - {self.time_minutes}分：{self.price}円"
