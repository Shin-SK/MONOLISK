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
        "get_store", "is_staff",
    )
    list_select_related = ("cast",)
    list_filter = ("is_staff",)

    # ----- helper columns -----
    @admin.display(description="源氏名")
    def get_stage_name(self, obj):
        return getattr(obj.cast, "stage_name", "—")

    @admin.display(description="アバター")
    def get_avatar(self, obj):
        cast = getattr(obj, "cast", None)
        if cast and cast.avatar:
            return format_html(
                '<img src="{}" style="height:40px;border-radius:50%;" />',
                cast.avatar.url,
            )
        return "—"

    @admin.display(description="店舗")
    def get_store(self, obj):
        if getattr(obj, "cast", None) and obj.cast.store:
            return obj.cast.store
        staff = getattr(obj, "staff", None)
        if staff and staff.stores.exists():
            return ", ".join(s.slug for s in staff.stores.all())
        if hasattr(obj, "store_profile"):
            return obj.store_profile.store
        return "—"
