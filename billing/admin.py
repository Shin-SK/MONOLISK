# billing/admin.py

from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import (
    Store, Table, ItemCategory, ItemMaster, Bill, BillItem,
    BillCastStay, Cast, CastPayout, ItemStock, BillingUser, CastCategoryRate, Customer
)
from django.contrib import admin
from .models import Store
from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from .resources import ItemCategoryRes, ItemMasterRes

User = get_user_model()  





class CastCategoryRateInline(admin.TabularInline):
    model = CastCategoryRate
    extra = 1


# ───────── マスター ─────────
class StoreForm(forms.ModelForm):
    class Meta:
        model  = Store
        fields = "__all__"
        widgets = {
            # 0.01 刻みで入力。 % ではなく「0.50 = 50%」方式に統一
            "nom_pool_rate": forms.NumberInput(attrs={"step": "0.01"}),
        }

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    form = StoreForm

    list_display  = ("name", "service_rate", "tax_rate", "nom_pool_rate", "business_day_cutoff_hour")
    list_editable = ("service_rate", "tax_rate", "nom_pool_rate")
    search_fields = ("name", "slug")  # ★追加：autocomplete用の検索項目

    fieldsets = (
        ("営業日設定", {"fields": ("business_day_cutoff_hour",)}),
        (None, {"fields": ("name", "slug")}),
        ("各種レート", {"fields": ("service_rate","tax_rate","nom_pool_rate")}),
    )
@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
	list_display  = ('store', 'code', 'seat_type')
	list_filter   = ('store','seat_type')
	search_fields = ('store__slug','code')
 
def __str__(self):
    return self.code or f'#{self.pk}'


@admin.register(Cast)
class CastAdmin(admin.ModelAdmin):
    # ───────── 一覧表示 ─────────
    list_display       = ("stage_name", "user_link", "store", "avatar_thumb")
    list_select_related = ("user", "store")
    search_fields      = ("stage_name", "user__username", "user__email")
    list_filter        = ("store",)
    inlines = [CastCategoryRateInline]

    # ───────── フォーム構成 ───────
    # ① 大量ユーザーでも軽い raw_id   ② “＋”ボタンでユーザー新規作成
    raw_id_fields = ("user",)

    readonly_fields = ("avatar_thumb",)

    fieldsets = (
        (None, {
            "fields": (
                "user",          # ← ここにプルダウン＋＋ボタン
                "stage_name",
                "store",
            )
        }),
        ("Back‑rate overrides", {
            "classes": ("collapse",),
            "fields": (
                "back_rate_free_override",
                "back_rate_nomination_override",
                "back_rate_inhouse_override",
            ),
        }),
        ("Avatar", {
            "fields": ("avatar", "avatar_thumb"),
        }),
    )

    # ───────── 便利表示 ───────────
    def avatar_thumb(self, obj):
        """Cloudinary / FileField サムネ (readonly)"""
        if obj.avatar:
            return mark_safe(
                f'<img src="{obj.avatar.url}" width="80" '
                'style="border-radius:4px;" />'
            )
        return "—"
    avatar_thumb.short_description = "Avatar"

    def user_link(self, obj):
        from django.contrib.auth import get_user_model  # ← ここで遅延 import
        User = get_user_model()
        if not obj.user_id:
            return "—"
        url = f"/admin/{User._meta.app_label}/{User._meta.model_name}/{obj.user_id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.user.username)

    user_link.short_description = "User"


# ★ 追加：カテゴリ ──────────────────────
@admin.register(ItemCategory)
class ItemCategoryAdmin(ImportExportModelAdmin):
    resource_classes = [ItemCategoryRes]
    list_display = ("code", "name", "show_in_menu",
                    "back_rate_free", "back_rate_nomination", "back_rate_inhouse",
                    "route")  # ←追加
    list_editable = ("back_rate_free", "back_rate_nomination", "back_rate_inhouse",
                     "route")  # ←追加


@admin.register(ItemMaster)
class ItemMasterAdmin(ImportExportModelAdmin):
    resource_classes = [ItemMasterRes]
    list_display  = ("store", "category", "code", "name",
                     "price_regular", "duration_min", "route", "effective_route",
                     "track_stock", "exclude_from_payout")
    list_filter   = ("store", "category", "track_stock", "exclude_from_payout", "route")
    search_fields = ("name", "code", "category__name")

    def effective_route(self, obj):
        from .models import ROUTE_INHERIT
        if obj.route == ROUTE_INHERIT:
            return getattr(obj.category, 'route', 'none')
        return obj.route
    effective_route.short_description = "実ルート"



@admin.register(ItemStock)
class ItemStockAdmin(admin.ModelAdmin):
	list_display  = ('item', 'qty')
	search_fields = ('item__name',)
	list_filter   = ('item__store',)


# ───────── 伝票 ─────────
class BillItemInline(admin.TabularInline):
	model               = BillItem
	extra               = 0
	autocomplete_fields = ('item_master', 'served_by_cast')
	readonly_fields     = ('subtotal',)

class BillCastStayInline(admin.TabularInline):
    model  = BillCastStay
    extra  = 0
    fields = ('cast', 'stay_type', 'entered_at', 'left_at')
    autocomplete_fields = ('cast',)
    list_display = ('bill', 'cast', 'stay_type', 'entered_at', 'left_at')


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display       = ('id', 'table', 'opened_at', 'closed_at', 'total', 'discount_rule')  # ← 追加
    list_filter        = ('table__store', 'closed_at', 'discount_rule')                        # ← 追加
    date_hierarchy     = 'opened_at'
    inlines = (BillItemInline, BillCastStayInline)
    filter_horizontal  = ('nominated_casts',)
    fieldsets = (
        (None, {'fields': ('table', 'opened_at', 'closed_at', 'expected_out', 'memo', 'discount_rule')}),  # ← 追加
        ('金額', {'fields': ('subtotal', 'service_charge', 'tax', 'grand_total', 'total', 'settled_total')}),
        ('支払', {'fields': ('paid_cash', 'paid_card')}),
        ('指名', {'fields': ('main_cast', 'nominated_casts')}),
    )


@admin.register(BillItem)
class BillItemAdmin(admin.ModelAdmin):
	list_display  = (
		'bill', 'name', 'qty', 'price', 'back_rate',
		'served_by_cast', 'exclude_from_payout', 'subtotal',
	)
	list_filter   = ('bill__table__store', 'served_by_cast', 'exclude_from_payout')
	search_fields = ('name',)


@admin.register(BillCastStay)
class BillCastStayAdmin(admin.ModelAdmin):
    list_display = ('bill', 'cast', 'entered_at', 'left_at')
    list_filter  = ('bill__table__store', 'cast')


@admin.register(CastPayout)
class CastPayoutAdmin(admin.ModelAdmin):
	list_display  = ('bill', 'cast', 'amount')
	list_filter   = ('cast', 'bill__table__store')
	search_fields = ('bill__id', 'cast__stage_name')






@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'display_name', 'phone', 'updated_at')
    search_fields = ('full_name', 'alias', 'phone')
    


from django.contrib import admin
from .models import StoreNotice

@admin.register(StoreNotice)
class StoreNoticeAdmin(admin.ModelAdmin):
    list_display  = ('title', 'store', 'is_published', 'publish_at', 'pinned', 'created_at')
    list_filter   = ('store', 'is_published', 'pinned')
    search_fields = ('title', 'body')
    date_hierarchy = 'publish_at'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('store', 'title', 'body')}),
        ('Cover', {'fields': ('cover',)}),
        ('Publish', {'fields': ('is_published', 'publish_at', 'pinned')}),
        ('System', {'fields': ('created_at', 'updated_at')}),
    )



from .models import OrderTicket

@admin.register(OrderTicket)
class OrderTicketAdmin(admin.ModelAdmin):
    list_display  = ('id','store','route','state','created_by_cast',
                     'created_at','acked_at','ready_at','taken_by_staff','taken_at','archived_at')
    list_filter   = ('store','route','state','created_by_cast','taken_by_staff')
    search_fields = ('bill_item__bill__id',)
    date_hierarchy = 'created_at'


# billing/admin.py（必要なimportを追加）
from django.utils import timezone
from django.contrib import messages
from .models import Staff, StaffShift

# ───────────────── StaffShift Inline（スタッフ詳細からも編集できるように）
class StaffShiftInline(admin.TabularInline):
    model = StaffShift
    extra = 0
    fields = ('store', 'plan_start', 'plan_end', 'clock_in', 'clock_out')
    show_change_link = True

# ───────────────── Staff を管理画面に登録（未登録なら）
@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display  = ('id', 'user', 'role', 'hourly_wage')
    list_filter   = ('role', 'stores')
    search_fields = ('user__username', 'user__email')
    filter_horizontal = ('stores',)
    inlines = [StaffShiftInline]

# ───────────────── StaffShift 管理画面
class ActiveShiftFilter(admin.SimpleListFilter):
    title = '稼働状態'
    parameter_name = 'active'

    def lookups(self, request, model_admin):
        return (
            ('planned', '予定のみ'),
            ('active',  '出勤中'),
            ('done',    '退勤済'),
        )

    def queryset(self, request, qs):
        v = self.value()
        if v == 'planned':
            return qs.filter(clock_in__isnull=True)
        if v == 'active':
            return qs.filter(clock_in__isnull=False, clock_out__isnull=True)
        if v == 'done':
            return qs.filter(clock_out__isnull=False)
        return qs

@admin.action(description='選択したレコードを「いま出勤」にする')
def action_clock_in_now(modeladmin, request, queryset):
    now = timezone.now()
    n = 0
    for sh in queryset:
        if sh.clock_in is None:
            sh.clock_in = now
            sh.save(update_fields=['clock_in'])
            n += 1
    messages.success(request, f'{n}件を出勤にしました')

@admin.action(description='選択したレコードを「いま退勤」にする')
def action_clock_out_now(modeladmin, request, queryset):
    now = timezone.now()
    n = 0
    for sh in queryset:
        if sh.clock_in and sh.clock_out is None:
            sh.clock_out = now
            sh.save(update_fields=['clock_out'])
            n += 1
    messages.success(request, f'{n}件を退勤にしました')

@admin.action(description='選択の出退勤をクリア（打刻なし）')
def action_clear_attendance(modeladmin, request, queryset):
    n = queryset.update(clock_in=None, clock_out=None, worked_min=None, payroll_amount=None)
    messages.info(request, f'{n}件の出退勤をクリアしました')

@admin.register(StaffShift)
class StaffShiftAdmin(admin.ModelAdmin):
    list_display  = ('id', 'store', 'staff', 'plan_start', 'plan_end', 'clock_in', 'clock_out', 'worked_min', 'payroll_amount')
    list_filter   = ('store', 'staff', ActiveShiftFilter)
    search_fields = ('staff__user__username', 'staff__user__email')
    date_hierarchy = 'plan_start'
    autocomplete_fields = ('staff', 'store')
    actions = [action_clock_in_now, action_clock_out_now, action_clear_attendance]




# 末尾付近の他の admin.register 群の近くに追加

from .models import DiscountRule

@admin.register(DiscountRule)
class DiscountRuleAdmin(admin.ModelAdmin):
    list_display  = ('name', 'code', 'amount_off', 'percent_off', 'is_active', 'created_at')
    list_filter   = ('is_active', 'is_basic')
    search_fields = ('name', 'code')
    prepopulated_fields = {'code': ('name',)}
