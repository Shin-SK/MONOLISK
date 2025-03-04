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
    # 既存
    customer_name = models.CharField(max_length=255, verbose_name="お客様の名前")
    start_time = models.DateTimeField(verbose_name="予約開始時刻")
    course = models.ForeignKey("Course", on_delete=models.CASCADE, null=True, blank=True)
    menus = models.ManyToManyField("Menu", blank=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, null=True, blank=True, verbose_name="店舗")
    cast = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations_as_cast')
    driver = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations_as_driver')
    
    # 追加: StoreUserを参照して、店舗・キャスト・ランク・星数を把握
    store_user = models.ForeignKey(
        StoreUser, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="店舗×キャスト"
    )

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
    )

    time_minutes = models.IntegerField(null=True, blank=True)
    reservation_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    discounts = models.ManyToManyField("Discount", blank=True)

    enrollment_fee = models.BooleanField(default=False)
    enrollment_fee_discounted = models.BooleanField(default=True)

    photo_nomination_fee = models.BooleanField(default=False)
    photo_nomination_fee_discounted = models.BooleanField(default=True)

    regular_nomination_fee = models.BooleanField(default=False)
    regular_nomination_fee_discounted = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        total_price = 0

        # 1) store_user があれば、そこから store, cast, rank, star_count を取得可能
        if self.store_user:
            # 予約時点で store/cast を自動的にセットしておきたいなら:
            self.store = self.store_user.store
            self.cast = self.store_user.user
            # rank や star_count は self.store_user.rank, self.store_user.star_count に入ってる

        # 2) コース料金 (StorePricing) など既存ロジック
        if self.course and self.store and self.time_minutes:
            pricing = StorePricing.objects.filter(
                store=self.store,
                course=self.course,
                time_minutes=self.time_minutes
            ).first()
            if pricing:
                total_price += pricing.price

        # 3) メニュー料金
        total_price += sum(menu.price for menu in self.menus.all())

        # 4) 入会金や写真指名、本指名などの追加オプション
        if self.enrollment_fee:
            total_price += 5000 if not self.enrollment_fee_discounted else 0
        if self.photo_nomination_fee:
            total_price += 2000 if not self.photo_nomination_fee_discounted else 0
        if self.regular_nomination_fee:
            total_price += 3000 if not self.regular_nomination_fee_discounted else 2000

        # 5) 割引
        total_discount = sum(discount.amount for discount in self.discounts.all())
        total_price -= total_discount

        # 6) ランク・星数を加味する場合はここで計算
        # 例: rank.plus_per_star * store_user.star_count を加算 etc.
        if self.store_user and self.store_user.rank:
            rank_obj = self.store_user.rank
            star = self.store_user.star_count or 0
            # 時間別料金を rank_obj から参照する場合は,
            #   total_price = rank_obj.price_XX + star * rank_obj.plus_per_star
            # などに切り替える
            # ただし今回は StorePricing と rank が別管理なので、運用に合わせて調整

        # 7) 予約金をセット
        self.reservation_amount = max(0, total_price)

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
