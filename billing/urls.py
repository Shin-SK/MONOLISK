# billing/urls.py
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedSimpleRouter
from .views import StoreViewSet, TableViewSet, ItemMasterViewSet, BillViewSet, BillItemViewSet, CastViewSet, CastSalesView, CastPayoutListView, CastItemDetailView, ItemCategoryViewSet
from billing.api.pl_views import DailyPLAPIView, MonthlyPLAPIView, YearlyPLAPIView
# --- Routers ---
router = DefaultRouter()
router.register(r'stores', StoreViewSet)
router.register(r'tables', TableViewSet)
router.register(r'item-masters', ItemMasterViewSet)
router.register(r'bills', BillViewSet, basename='bill')
router.register(r'casts', CastViewSet)
router.register(r'item-categories',  ItemCategoryViewSet)

bill_items_router = NestedSimpleRouter(router, r'bills', lookup='bill')
bill_items_router.register(r'items', BillItemViewSet, basename='bill-item')

# --- 追加の PL エンドポイント ---
extra_patterns = [
    path("pl/daily/",   DailyPLAPIView.as_view(),   name="billing-pl-daily"),
    path("pl/monthly/", MonthlyPLAPIView.as_view(), name="billing-pl-monthly"),
    path("pl/yearly/",  YearlyPLAPIView.as_view(),  name="billing-pl-yearly"),
    path('cast-sales/', CastSalesView.as_view(), name='cast-sales'),
    path('cast-payouts/', CastPayoutListView.as_view(), name='cast-payouts'),
    path('cast-items/', CastItemDetailView.as_view(), name='cast-items'),
]

# --- ぜんぶまとめる ---
urlpatterns = router.urls + bill_items_router.urls + extra_patterns
