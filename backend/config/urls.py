from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/accounts/", include("account.urls")),
    path("api/reservations/", include("reservation.urls")),
    path('api/sales/', include('sales.urls')),  # 売上APIのエンドポイントを追加
]
