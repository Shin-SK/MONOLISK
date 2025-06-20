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
	Reservation, ReservationCast, ReservationCharge, CashFlow
)

from .resources import RankCourseRes
from import_export import resources
from import_export.admin import ImportExportModelAdmin




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
	inlines	  = [CastCourseInline, CastOptionInline]


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



# ---------- 顧客・ドライバー ----------
@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
	list_display = ('id', 'driver_name', 'store')
	list_filter  = ('store',)

	@admin.display(description='Driver')
	def driver_name(self, obj):
		return obj.user.display_name or obj.user.username


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'phone')
	search_fields = ('name', 'phone')

# ---------- 予約 ----------

class ReservationForm(forms.ModelForm):
	class Meta:
		model  = Reservation
		fields = "__all__"

	def clean(self):
		data = super().clean()
		rc: RankCourse | None = data.get("rank_course")
		if rc:
			data["total_time"] = rc.course.minutes   # ← 自動コピー
		return data

class ReservationCastInline(admin.TabularInline):
	model = ReservationCast
	extra = 0

class ReservationChargeInline(admin.TabularInline):
	model = ReservationCharge
	extra = 0


class CashFlowInline(admin.TabularInline):
	model = CashFlow
	extra = 0



# ---------- CashFlow (単体表示も欲しい場合) ----------
@admin.register(CashFlow)
class CashFlowAdmin(admin.ModelAdmin):
	list_display = ('id', 'reservation', 'type', 'amount', 'recorded_at')
	list_filter = ('type', 'recorded_at')




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


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
	form = ReservationForm # total_time 自動入力
	inlines  = [ReservationCastInline,
				ReservationChargeInline,
				CashFlowInline]
	list_display = ('id', 'store', 'start_at', 'status',
					'expected_amount', 'discrepancy_flag')
	list_filter  = ('store', 'status', 'discrepancy_flag')
	date_hierarchy = 'start_at'