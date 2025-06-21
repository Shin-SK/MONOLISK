# config/urls.py
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseNotFound
from django.views.generic import TemplateView
from django.contrib.auth.forms import AuthenticationForm

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

# ログインアウト画面制作用

# if settings.DEBUG:
#     urlpatterns += [
#         # ログアウト画面プレビュー → http://localhost:8000/_preview/logout/
#         path(
#             "_preview/logout/",
#             TemplateView.as_view(
#                 template_name="registration/logged_out.html",
#                 extra_context={
#                     # logged_out.html で {{ user }} 等を使っている場合は
#                     # 適当にダミー値を入れておくと安心
#                     "user": None,
#                 },
#             ),
#             name="logout-preview",
#         ),

#         # ログイン画面プレビュー  → http://localhost:8000/_preview/login/
#         path(
#             "_preview/login/",
#             TemplateView.as_view(
#                 template_name="registration/login.html",
#                 extra_context={
#                     # ログインフォームを実際に表示したいなら
#                     "form": AuthenticationForm(),
#                 },
#             ),
#             name="login-preview",
#         ),
#     ]