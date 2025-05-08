from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Store, StoreUser, Rank

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = (
        'username', 'full_name', 'role',
        'is_staff', 'is_active', 'get_store_nicknames'
    )
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('full_name', 'role')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('full_name', 'role')}),
    )

class StoreUserInline(admin.TabularInline):
    model = StoreUser
    extra = 1
    fields = ('user', 'rank', 'star_count', 'nickname', 'cast_photo')

class StoreAdmin(admin.ModelAdmin):
    inlines = [StoreUserInline]

@admin.register(StoreUser)
class StoreUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'store', 'rank', 'star_count', 'nickname')

@admin.register(Rank)
class RankAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'price_60',
        'price_75',
        'price_90',
        'price_120',
        'price_150',
        'price_180',
        'price_extension_30',
        'plus_per_star',
    )

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Store, StoreAdmin)
