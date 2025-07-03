from django.contrib import admin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django import forms
from .models import (
	Store, Rank, Course, RankCourse, Option, GroupOptionPrice,
	CastProfile, CastCoursePrice, CastOption,
	Driver, Customer, Performer,
	Reservation, ReservationCast, ReservationCharge, CashFlow, DriverShift,
	ReservationDriver, CastRate ,DriverRate
)

from .resources import RankCourseRes
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .forms import ReservationForm




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
class RankCourseAdmin(ImportExportModelAdmin):
	resource_classes = [RankCourseRes]
	list_display = ('id', 'store', 'rank', 'course', 'base_price', 'star_increment')
	list_filter = ('store', 'rank')

@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'default_price', 'category')
	list_display_links = ('id', 'name')
	list_filter = ('category',)

@admin.register(GroupOptionPrice)
class GroupOptionPriceAdmin(admin.ModelAdmin):
	list_display = ('id', 'store', 'participants', 'course', 'price')
	list_filter = ('store', 'participants')


# ─ Performer 用 ImportExport リソース（← 追加）
class PerformerRes(resources.ModelResource):
	class Meta:
		model = Performer
		import_id_fields = ("id",)

@admin.register(Performer)
class PerformerAdmin(ImportExportModelAdmin):
	resource_classes = [PerformerRes]
	list_display = ("id", "real_name", "birthday")
	list_display_links = ('id', 'real_name')


# ─ CastProfile ───────────────────────
# ───────── インラインを先に定義 ─────────
class CastCourseInline(admin.TabularInline):
	model = CastCoursePrice
	extra = 0
	fields = ("course", "custom_price")
	readonly_fields = ("course",)

class CastOptionInline(admin.TabularInline):
	model = CastOption
	extra = 0

# ───────── ImportExport 用リソース ──────
class CastProfileRes(resources.ModelResource):
	class Meta:
		model = CastProfile
		import_id_fields = ("id",)

# CastRate を Cast 内で編集する用インライン
class CastRateInline(admin.TabularInline):
    model = CastRate
    extra = 0
    fields = ("hourly_rate", "commission_pct", "effective_from")
    ordering = ("-effective_from",)
# ───────── 登録はこれ 1 つだけ ───────────
@admin.register(CastProfile)
class CastProfileAdmin(ImportExportModelAdmin):
	resource_classes = [CastProfileRes]

	list_display = (
		"id", "stage_name", "store", "rank",
		"star_count", "price_mode", "performer_real", "photo_tag"
	)
	readonly_fields = ('photo_tag',)
	list_filter  = ("store", "rank", "price_mode")
	inlines = [CastCourseInline, CastOptionInline, CastRateInline]


	def photo_tag(self, obj):
		if obj.photo:
			return format_html('<img src="{}" width="60" />', obj.photo.url)
		return '-'
	photo_tag.short_description = 'Photo'


	@admin.display(description="本名")
	def performer_real(self, obj):
		return obj.performer.real_name

	def save_model(self, request, obj, form, change):
		super().save_model(request, obj, form, change)
		# Course
		CastCoursePrice.objects.bulk_create([
			CastCoursePrice(cast_profile=obj, course=c)
			for c in Course.objects.exclude(
				id__in=obj.castcourseprice_set.values_list("course_id", flat=True)
			)
		])
		# Option
		CastOption.objects.bulk_create([
			CastOption(cast_profile=obj, option=o)
			for o in Option.objects.exclude(
				id__in=obj.castoption_set.values_list("option_id", flat=True)
			)
		])


# ---------- CashFlow (単体表示も欲しい場合) ----------
@admin.register(CashFlow)
class CashFlowAdmin(admin.ModelAdmin):
	list_display = ('id', 'reservation', 'type', 'amount', 'recorded_at')
	list_filter = ('type', 'recorded_at')



# ---------- 顧客・ドライバー ----------


class DriverRateInline(admin.TabularInline):
    model = DriverRate
    extra = 0
    fields = ("hourly_rate", "effective_from")
    ordering = ("-effective_from",)


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
	list_display = ('id', 'driver_name', 'store')
	list_filter  = ('store',)
	search_fields = (		   # ← これを追加
		'user__username',
		'user__display_name',
		'user__email',
	)
	inlines = [DriverRateInline]

	@admin.display(description='Driver')
	def driver_name(self, obj):
		return obj.user.display_name or obj.user.username


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'phone')
	list_display_links = ('id', 'name')
	search_fields = ('name', 'phone')



# ---------- ユーザー ----------

User = get_user_model()

@admin.register(User)
class UserAdmin(BaseUserAdmin):
	list_display  = ("id", "username", "display_name", "email",
					 "is_staff", "is_active", "thumb")
	list_filter   = ("is_staff", "is_active")
	search_fields = ("username", "display_name", "email")
	readonly_fields = ("thumb",)

	# ───── ここを１つにまとめる ─────
	fieldsets = BaseUserAdmin.fieldsets + (
		("Extra", {"fields": ("display_name", "avatar")}),
	)
	#  └─ これで重複ゼロ。『Personal info』の追加行は削除

	# 新規追加フォーム (createsuperuser 用)
	add_fieldsets = BaseUserAdmin.add_fieldsets + (
		(None, {
			"classes": ("wide",),
			"fields": ("display_name", "avatar"),   # ← avatar も追加可
		}),
	)

	def thumb(self, obj):
		if obj.avatar:
			return format_html(
				'<img src="{}" style="height:40px;border-radius:50%;" />',
				obj.avatar.url,
			)
		return "-"
	thumb.short_description = "Avatar"

# ---------- 予約 ----------


class ReservationCastInline(admin.TabularInline):
	model   = ReservationCast
	fields  = ("cast_profile", "course")
	extra   = 0
	# ↓ クラスを３つセット（collapse は折りたたみ表示を防ぐため無しでも可）
	classes = ( "tab-reserve", "extrapretty", "wide")  # ★ tab-reserve に統一
	

class ReservationChargeInline(admin.TabularInline):
	model   = ReservationCharge
	extra   = 0
	classes = ("tab-reserve","extrapretty", "wide")  # ★ 同じタブへ

class CashFlowInline(admin.TabularInline):
	model   = CashFlow
	extra   = 0
	classes = ( "tab-money", "extrapretty", "wide")	# 金額タブは別



@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
	form = ReservationForm
	inlines = []
	search_fields = (
		'id',
		'customer__name',
		'customer__phone',
		'store__name',
	)

	def get_form(self, request, obj=None, **kwargs):
		form = super().get_form(request, obj, **kwargs)
		store_id = request.GET.get("store")
		qs = CastProfile.objects.filter(store_id=store_id) if store_id else CastProfile.objects.all()
		form.base_fields["cast_profile"].queryset = qs
		return form


	fieldsets = (
		('予約情報', {'fields': (
			'store', 'cast_profile', 'start_at', 'course', 'customer',
		)}),
		('金額', {'fields': ('manual_extra_price', 'received_amount')}),
		('その他', {'classes': ('collapse',), 'fields': ('driver', 'status')}),
	)


	list_display	   = ('id', 'store', 'start_at', 'customer')
	list_filter		= ('store', 'status')
	date_hierarchy	 = 'start_at'

	# ───────── カスタム列 ──────────
	@admin.display(description='キャスト', ordering='casts__cast_profile__stage_name')
	def cast_column(self, obj):
		"""
		予約に紐づくキャストを ➜ [写真] 名前 で表示。
		複数キャストの場合は改行区切り。
		"""
		if not obj.casts.exists():
			return '-'

		html_parts = []
		for rc in obj.casts.all():
			cp = rc.cast_profile
			html_parts.append(
				'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
				f'<img src="{cp.photo_url}" style="width:32px;height:32px;border-radius:50%;object-fit:cover;">'
				f'<span>{cp.stage_name}</span></div>'
			)
		return format_html(''.join(html_parts))

	@admin.display(description='ドライバー', ordering='driver__user__username')
	def driver_column(self, obj):
		return obj.driver  # Driver.__str__() でユーザー名を返している


from django.contrib import admin
from .models import ShiftPlan, ShiftAttendance

@admin.register(ShiftPlan)
class ShiftPlanAdmin(admin.ModelAdmin):
	list_display  = ("date", "cast_profile", "store", "start_at", "end_at")
	list_filter   = ("store", "date")
	search_fields = ("cast_profile__stage_name",)

@admin.register(ShiftAttendance)
class ShiftAttendanceAdmin(admin.ModelAdmin):
	list_display  = ("cast_profile", "checked_in", "checked_in_at", "shift_plan")
	list_filter   = ("checked_in", "checked_in_at")
	actions	   = ["make_checkin"]

	@admin.action(description="選択レコードを打刻済みにする")
	def make_checkin(self, request, queryset):
		for att in queryset:
			att.checkin()



@admin.register(DriverShift)
class DriverShiftAdmin(admin.ModelAdmin):
	list_display  = ('id', 'driver', 'date', 'clock_in_at', 'clock_out_at')
	list_filter   = ('date', 'driver__store')
	search_fields = ('driver__user__username', 'driver__user__display_name')



@admin.register(ReservationDriver)
class ReservationDriverAdmin(admin.ModelAdmin):
    """PU/DO 中間テーブル（start_at / end_at は廃止済み）"""
    list_display = (
        'id', 'reservation', 'driver',      # 基本
        'role', 'collected_amount', 'status',
    )
    list_filter  = ('role', 'status', 'driver__store')
    autocomplete_fields = ('reservation', 'driver')
    search_fields = (
        'reservation__id',
        'driver__user__username',
        'driver__user__display_name',
    )



# core/admin.py  最後の方などに追記
from .models import ExpenseCategory, ExpenseEntry

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display  = ('id', 'name', 'code', 'is_fixed', 'is_active')
    list_filter   = ('is_fixed', 'is_active')
    search_fields = ('name', 'code')
    ordering      = ('code',)

@admin.register(ExpenseEntry)
class ExpenseEntryAdmin(admin.ModelAdmin):
    list_display   = ('id', 'date', 'store', 'category', 'label', 'amount')
    list_filter    = ('store', 'category')
    search_fields  = ('label',)
    date_hierarchy = 'date'
