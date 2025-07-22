# billing/admin.py  （TAB インデント）

from django.contrib import admin
from .models import Store, Table, ItemCategory, ItemMaster, Bill, BillItem, BillCastStay, Cast, CastPayout, ItemStock, UserStore
from django.utils.safestring import mark_safe
from django.contrib.auth import get_user_model
from django.utils.html import format_html

# ───────── マスター ─────────
@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
	list_display  = ('slug', 'name', 'service_rate', 'tax_rate')
	search_fields = ('slug', 'name')


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
	list_display  = ('store', 'number')
	list_filter   = ('store',)
	search_fields = ('store__slug',)


@admin.register(Cast)
class CastAdmin(admin.ModelAdmin):
    # ───────── 一覧表示 ─────────
    list_display       = ("stage_name", "user_link", "store", "avatar_thumb")
    list_select_related = ("user", "store")
    search_fields      = ("stage_name", "user__username", "user__email")
    list_filter        = ("store",)

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
        """ユーザー編集画面へのリンク付き表示"""
        if not obj.user_id:
            return "—"
        url = (
            f"/admin/{User._meta.app_label}/"
            f"{User._meta.model_name}/{obj.user_id}/change/"
        )
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = "User"


# ★ 追加：カテゴリ ──────────────────────
@admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name',
                    'back_rate_free', 'back_rate_nomination', 'back_rate_inhouse')
    list_editable = ('back_rate_free', 'back_rate_nomination', 'back_rate_inhouse')


# 改訂版 ItemMaster
@admin.register(ItemMaster)
class ItemMasterAdmin(admin.ModelAdmin):
    list_display = (
        'store', 'category', 'name',
        'price_regular', 'price_late',
        'track_stock', 'exclude_from_payout',
    )
    list_filter   = ('store', 'category', 'track_stock', 'exclude_from_payout')
    search_fields = ('name',)


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
	list_display       = ('id', 'table', 'opened_at', 'closed_at', 'total')
	list_filter        = ('table__store', 'closed_at')
	date_hierarchy     = 'opened_at'
	inlines = (BillItemInline, BillCastStayInline)
	filter_horizontal  = ('nominated_casts',)


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



@admin.register(UserStore)
class UserStoreAdmin(admin.ModelAdmin):
    list_display  = ('user', 'store')
    list_select_related = ('store',)
    search_fields = ('user__username', 'store__name')



from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from billing.models import Store

User = get_user_model()

class UserAdmin(BaseUserAdmin):
    # ▶ 既存 fieldsets に store を足すだけ
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Billing', {'fields': ('store',)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Billing', {'fields': ('store',)}),
    )
    list_display = ('username', 'email', 'store', 'is_staff', 'is_superuser')
    list_filter  = ('is_staff', 'is_superuser', 'store')

# いったん既存の登録を外してから再登録
admin.site.unregister(User)
admin.site.register(User, UserAdmin)