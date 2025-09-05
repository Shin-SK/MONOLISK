# accounts/admin.py
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from accounts.resources import UserRes

from billing.models import Cast, Staff

User = get_user_model()


class CastInline(admin.StackedInline):
    model = Cast
    extra = 0
    can_delete = False


class StaffInline(admin.StackedInline):
    model = Staff
    extra = 0
    can_delete = False


@admin.register(User)
class CustomUserAdmin(ImportExportModelAdmin, BaseUserAdmin):
    resource_class = UserRes
    inlines = (CastInline, StaffInline)

    list_display = (
        "username", "get_stage_name", "get_avatar",
        "store", "is_staff",
    )
    list_filter  = ("is_staff", "store")
    search_fields = ("username", "email", "store__name")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("個人情報", {"fields": ("first_name", "last_name", "email")}),
        ("所属店舗", {"fields": ("store",)}),         # ★ 追加
        ("権限", {"fields": ("is_active", "is_staff", "is_superuser",
                            "groups", "user_permissions")}),
        ("日付", {"fields": ("last_login", "date_joined")}),
    )

    @admin.display(description="アバター")
    def get_avatar(self, obj):
        cast = getattr(obj, "cast", None)
        return format_html('<img src="{}" style="height:40px;border-radius:50%;" />',
                           cast.avatar.url) if cast and cast.avatar else "—"

    @admin.display(description="源氏名")
    def get_stage_name(self, obj):
        return getattr(obj.cast, "stage_name", "—")



# accounts/admin.py
from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import StoreMembership, StoreRole

User = get_user_model()

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
