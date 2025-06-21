# config/urls.py
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseNotFound
from django.views.generic import TemplateView, RedirectView
from django.contrib.auth.forms import AuthenticationForm
from core.autocomplete import CustomerByPhone

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="admin:index", permanent=False)),


    path("admin/", admin.site.urls),

    # ---------- API ----------
    path("api/", include("core.urls")),
    path("api/auth/registration/", include("dj_rest_auth.registration.urls")),
    path("api/dj-rest-auth/", include("dj_rest_auth.urls")),
    path("ac/", include("core.autocomplete")),

]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )

