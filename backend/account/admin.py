from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Store, StoreUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'full_name', 'role', 'is_staff', 'is_active', 'get_store_nicknames')  # 🔥 店舗ニックネームを表示
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('full_name', 'role')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('full_name', 'role')}),
    )

class StoreUserInline(admin.TabularInline):  # 🔥 ユーザー編集画面で店舗ニックネームを直接編集できる
    model = StoreUser
    extra = 1

class StoreAdmin(admin.ModelAdmin):
    inlines = [StoreUserInline]

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Store, StoreAdmin)
admin.site.register(StoreUser)  # 🔥 店舗-ユーザー-ニックネームの管理を追加
