# config/urls.py
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseNotFound
from django.views.generic import TemplateView, RedirectView
from django.contrib.auth.forms import AuthenticationForm

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="admin:index", permanent=False)),


    path("admin/", admin.site.urls),

    # ---------- API ----------
    path('api/billing/', include('billing.urls')), 
    path("api/auth/registration/", include("dj_rest_auth.registration.urls")),
    path("api/dj-rest-auth/", include("dj_rest_auth.urls")),
 
    # accounts API は /api/accounts/ 配下に統一
    path('api/accounts/', include('accounts.urls')),
    # 互換: 旧 /api/me/ も維持
    path('api/me/', __import__('accounts.views', fromlist=['me']).me),
 
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )

