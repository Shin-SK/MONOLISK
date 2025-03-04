from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, StoreCastsAPIView, StoreListView

# DRFのルーターを作成
router = DefaultRouter()
router.register(r'users', UserViewSet)  # /api/accounts/users/

urlpatterns = [
    path('', include(router.urls)),  # ViewSetのURLを自動生成
    path("casts/", StoreCastsAPIView.as_view(), name="store-casts"),  # 🔥 追加
    path("stores/", StoreListView.as_view(), name="store-list"),  # 🔥 店舗一覧を追加
]
