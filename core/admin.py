from django.contrib import admin
from django.contrib.auth.models import Group
from .models import (
    Store, Rank, Course, RankCourse, Option, GroupOptionPrice,
    Cast, CastCoursePrice, CastOption,
    Driver, Customer,
    Reservation, ReservationCast, ReservationCharge, CashFlow
)
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model

# ---------- マスタ ----------
@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'address')
    search_fields = ('name',)

@admin.register(Rank)
class RankAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'minutes', 'is_pack')
    list_filter = ('is_pack',)

@admin.register(RankCourse)
class RankCourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'store', 'rank', 'course', 'base_price', 'star_increment')
    list_filter = ('store', 'rank')

@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'default_price', 'category')
    list_filter = ('category',)

@admin.register(GroupOptionPrice)
class GroupOptionPriceAdmin(admin.ModelAdmin):
    list_display = ('id', 'store', 'participants', 'course', 'price')
    list_filter = ('store', 'participants')

# ---------- キャスト ----------
class CastCourseInline(admin.TabularInline):
    model = CastCoursePrice
    extra = 0

class CastOptionInline(admin.TabularInline):
    model = CastOption
    extra = 0

@admin.register(Cast)
class CastAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'store', 'rank', 'star_count', 'price_mode')
    list_filter = ('store', 'rank', 'price_mode')
    inlines = [CastCourseInline, CastOptionInline]

# ---------- 顧客・ドライバー ----------
@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'store')
    list_filter = ('store',)

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'phone')
    search_fields = ('name', 'phone')

# ---------- 予約 ----------
class ReservationCastInline(admin.TabularInline):
    model = ReservationCast
    extra = 0

class ReservationChargeInline(admin.TabularInline):
    model = ReservationCharge
    extra = 0

class CashFlowInline(admin.TabularInline):
    model = CashFlow
    extra = 0

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'store', 'start_at', 'status',
        'expected_amount', 'discrepancy_flag'
    )
    list_filter = ('store', 'status', 'discrepancy_flag')
    date_hierarchy = 'start_at'
    inlines = [ReservationCastInline, ReservationChargeInline, CashFlowInline]

# ---------- CashFlow (単体表示も欲しい場合) ----------
@admin.register(CashFlow)
class CashFlowAdmin(admin.ModelAdmin):
    list_display = ('id', 'reservation', 'type', 'amount', 'recorded_at')
    list_filter = ('type', 'recorded_at')




User = get_user_model()

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    - username / email / password は標準
    - Groups タブで STAFF / DRIVER / CAST を付与
    """
    list_display = ("id", "username", "email", "is_staff", "is_active")
    list_filter  = ("is_staff", "is_active")
    search_fields = ("username", "email")
