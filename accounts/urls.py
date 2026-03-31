# accounts/urls.py
from django.urls import path
from .views import me, debug_set_role, contact

urlpatterns = [
    # /api/accounts/me/
    path('me/', me, name='me'),
    # デバッグ用は /api/accounts/debug/set-role/
    path('debug/set-role/', debug_set_role),
    # お問い合わせ
    path('contact/', contact, name='contact'),
]