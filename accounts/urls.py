# accounts/urls.py
from django.urls import path
from .views import me, debug_set_role

urlpatterns = [
    path('me/', me, name='me'),
    path('accounts/debug/set-role/', debug_set_role),
]