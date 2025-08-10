# billing/urls.pyhttps://desktop.postman.com/?desktopVersion=11.56.4&webVersion=11.56.4-ui-250801-0111&userId=37159453&teamId=0&region=us
from django.urls import path
from rest_framework.routers          import DefaultRouter
from rest_framework_nested.routers   import NestedSimpleRouter, NestedDefaultRouter
from billing.api.pl_views import DailyPLAPIView, MonthlyPLAPIView, YearlyPLAPIView
from .views import StoreViewSet, TableViewSet, ItemMasterViewSet, BillViewSet, BillItemViewSet, CastViewSet, CastSalesView, CastPayoutListView, CastItemDetailView, ItemCategoryViewSet, CastShiftViewSet, CastDailySummaryViewSet, CastRankingView, StaffViewSet, StaffShiftViewSet, BillViewSet, BillStayViewSet, CustomerViewSet, StoreNoticeViewSet

# --- Routers ---
router = DefaultRouter()
router.register(r'stores', StoreViewSet)
router.register(r'tables', TableViewSet)
router.register(r'item-masters', ItemMasterViewSet)
router.register(r'bills', BillViewSet, basename='bill')
router.register(r'casts', CastViewSet)
router.register(r'item-categories',  ItemCategoryViewSet)
router.register(r'cast-shifts', CastShiftViewSet)
router.register(r'cast-daily-summaries', CastDailySummaryViewSet, basename='cast-daily-summaries')
router.register(r'staffs', StaffViewSet, basename='staff')
router.register(r'staff-shift-plans', StaffShiftViewSet, basename='staff-shift-plan')
router.register(r'customers', CustomerViewSet)
router.register(r'store-notices', StoreNoticeViewSet, basename='store-notice')

bill_items_router = NestedSimpleRouter(router, r'bills', lookup='bill')
bill_items_router.register(r'items', BillItemViewSet, basename='bill-item')

bills_router = NestedDefaultRouter(router, r'bills', lookup='bill')
bills_router.register(r'stays', BillStayViewSet, basename='bill-stays')

# --- 追加の PL エンドポイント ---
extra_patterns = [
    path("pl/daily/",   DailyPLAPIView.as_view(),   name="billing-pl-daily"),
    path("pl/monthly/", MonthlyPLAPIView.as_view(), name="billing-pl-monthly"),
    path("pl/yearly/",  YearlyPLAPIView.as_view(),  name="billing-pl-yearly"),
    path('cast-sales/', CastSalesView.as_view(), name='cast-sales'),
    path('cast-payouts/', CastPayoutListView.as_view(), name='cast-payouts'),
    path('cast-items/', CastItemDetailView.as_view(), name='cast-items'),
    path('cast-rankings/', CastRankingView. as_view(), name='cast-rankings'),
]

# --- ぜんぶまとめる ---
urlpatterns = (
      router.urls
    + bill_items_router.urls
    + bills_router.urls
    + extra_patterns
)

