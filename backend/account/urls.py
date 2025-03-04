from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, StoreUserViewSet, 
    StoreListView, StoreCastsAPIView,
    RankViewSet  # 追加
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'store-users', StoreUserViewSet, basename='store-users')
router.register(r'ranks', RankViewSet, basename='ranks')  # 追加

urlpatterns = [
    path('stores/', StoreListView.as_view(), name='store-list'),
    path('casts/', StoreCastsAPIView.as_view(), name='store-casts'),
    path('', include(router.urls)),
]
