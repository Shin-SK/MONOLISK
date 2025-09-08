# accounts/admin.py
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from django import forms  # ★ 追加

from accounts.resources import UserRes
from accounts.models import StoreMembership, StoreRole
from billing.models import Cast, Staff, Store  # ★ Store を使う

User = get_user_model()


# ───────── Inlines ─────────
class CastInline(admin.StackedInline):
    model = Cast
    extra = 0
    can_delete = False


class StaffInline(admin.StackedInline):
    model = Staff
    extra = 0
    can_delete = False


class StoreMembershipInline(admin.TabularInline):
    model = StoreMembership
    extra = 0
    autocomplete_fields = ('store',)
    fields = ('store', 'role', 'is_primary')


# ───────── 一括アクション用フォーム（ユーザー一覧に表示） ─────────
from django.contrib.admin.helpers import ActionForm

class MembershipActionForm(ActionForm):
    store = forms.ModelChoiceField(queryset=Store.objects.all(), required=True, label='Store')
    role  = forms.ChoiceField(choices=StoreRole.choices, required=True, label='Role')
    make_primary = forms.BooleanField(required=False, initial=True, label='主所属にする')


# ───────── User Admin ─────────
@admin.register(User)
class CustomUserAdmin(ImportExportModelAdmin, BaseUserAdmin):
    resource_class = UserRes
    inlines = (CastInline, StaffInline, StoreMembershipInline)

    list_display = ("username", "get_stage_name", "get_avatar", "store", "is_staff")
    list_filter  = ("is_staff", "store")
    search_fields = ("username", "email", "store__name")
    list_select_related = ("store",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("個人情報", {"fields": ("first_name", "last_name", "email")}),
        ("所属店舗", {"fields": ("store",)}),  # 既存フィールド（将来はMembership中心に）
        ("権限", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("日付", {"fields": ("last_login", "date_joined")}),
    )

    # 一覧アクション（選択ユーザーに所属付与）
    action_form = MembershipActionForm
    actions = ['action_add_membership']

    @admin.action(description='選択ユーザーに所属店舗/ロールを付与')
    def action_add_membership(self, request, queryset):
        store = request.POST.get('store')
        role  = request.POST.get('role')
        make_primary = bool(request.POST.get('make_primary'))
        if not store or not role:
            self.message_user(request, 'store と role は必須です', level='error')
            return
        store_obj = Store.objects.get(pk=store)
        n = 0
        for u in queryset:
            mem, _ = StoreMembership.objects.get_or_create(
                user=u, store=store_obj,
                defaults={'role': role, 'is_primary': make_primary}
            )
            updated = False
            if mem.role != role:
                mem.role = role
                updated = True
            if make_primary and not mem.is_primary:
                StoreMembership.objects.filter(user=u).update(is_primary=False)
                mem.is_primary = True
                updated = True
            if updated:
                mem.save()
            n += 1
        self.message_user(request, f'{n}件更新しました')

    # 表示用
    @admin.display(description="アバター")
    def get_avatar(self, obj):
        cast = getattr(obj, "cast", None)
        return format_html(
            '<img src="{}" style="height:40px;border-radius:50%;" />',
            cast.avatar.url
        ) if cast and cast.avatar else "—"

    @admin.display(description="源氏名")
    def get_stage_name(self, obj):
        return getattr(getattr(obj, "cast", None), "stage_name", "—")


# ───────── StoreMembership Admin（主所属切替アクション） ─────────
@admin.action(description='主所属に設定（他は解除）')
def make_primary(modeladmin, request, queryset):
    for m in queryset:
        StoreMembership.objects.filter(user=m.user).exclude(pk=m.pk).update(is_primary=False)
        if not m.is_primary:
            m.is_primary = True
            m.save(update_fields=['is_primary'])

@admin.register(StoreMembership)
class StoreMembershipAdmin(admin.ModelAdmin):
    list_display  = ('user', 'store', 'role', 'is_primary')
    list_filter   = ('role', 'is_primary', 'store')
    search_fields = ('user__username', 'user__email', 'store__name')
    autocomplete_fields = ('user', 'store')
    actions = [make_primary]
