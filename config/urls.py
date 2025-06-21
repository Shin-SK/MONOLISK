# config/urls.py
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseNotFound

urlpatterns = [
    path("admin/", admin.site.urls),

    # ---------- API ----------
    path("api/", include("core.urls")),
    path("api/auth/registration/", include("dj_rest_auth.registration.urls")),
    path("api/dj-rest-auth/", include("dj_rest_auth.urls")),   # ← これ
    path('autocomplete/', include('core.autocomplete')),  # ← 追加
    
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )