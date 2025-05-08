from django.contrib import admin
from .models import Reservation, Course, Menu, StorePricing, Discount

class ReservationAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "start_time", "store", "get_cast_name", "get_driver_name", "reservation_amount", "get_discounts")
    list_filter = ("store", "cast")  # 'cast'フィールドでフィルタリング
    search_fields = ("customer_name", "cast__full_name", "driver__full_name")  # 'cast'と'driver'のフルネームで検索

    def get_cast_name(self, obj):
        return obj.cast.full_name if obj.cast else "なし"
    get_cast_name.short_description = "キャスト名"

    def get_driver_name(self, obj):
        return obj.driver.full_name if obj.driver else "なし"
    get_driver_name.short_description = "ドライバー名"

    def get_discounts(self, obj):
        """適用された割引の一覧を表示"""
        return ", ".join([f"{d.name} (-{d.amount}円)" for d in obj.discounts.all()])
    get_discounts.short_description = "適用割引"

admin.site.register(Reservation, ReservationAdmin)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "price")

@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ("name", "price")

@admin.register(StorePricing)
class StorePricingAdmin(admin.ModelAdmin):
    list_display = ("store", "course", "time_minutes", "price")  # 'membership_type' 削除
    list_filter = ("store", "course")
    search_fields = ("store__name", "course__name")

@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ("name", "amount")
