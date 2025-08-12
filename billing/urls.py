from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    StoreViewSet, TableViewSet, ItemMasterViewSet,
    BillViewSet, BillItemViewSet, BillStayViewSet,
    CastViewSet, CastSalesView, CastSalesSummaryView,
    CastPayoutListView, CastItemDetailView,
    ItemCategoryViewSet, CastShiftViewSet,
    CastDailySummaryViewSet, CastRankingView,
    StaffViewSet, StaffShiftViewSet,
    CustomerViewSet, StoreNoticeViewSet,
)

router = DefaultRouter()
router.register(r"stores",               StoreViewSet,           basename="stores")
router.register(r"tables",               TableViewSet,           basename="tables")
router.register(r"item-masters",         ItemMasterViewSet,      basename="item-masters")
router.register(r"bills",                BillViewSet,            basename="bills")
router.register(r"casts",                CastViewSet,            basename="casts")
router.register(r"item-categories",      ItemCategoryViewSet,    basename="item-categories")
router.register(r"cast-shifts",          CastShiftViewSet,       basename="cast-shifts")
router.register(r"cast-daily-summaries", CastDailySummaryViewSet,basename="cast-daily-summaries")
router.register(r"staff",                StaffViewSet,           basename="staff")
router.register(r"staff-shifts",         StaffShiftViewSet,      basename="staff-shifts")
router.register(r"customers",            CustomerViewSet,        basename="customers")
router.register(r"store-notices",        StoreNoticeViewSet,     basename="store-notices")

urlpatterns = [
    # ルーター系
    path("", include(router.urls)),

    # Bill 配下のネスト（drf-nestedなしで明示）
    path("bills/<int:bill_pk>/items/",
         BillItemViewSet.as_view({"get": "list", "post": "create"}), name="billitem-list"),
    path("bills/<int:bill_pk>/items/<int:pk>/",
         BillItemViewSet.as_view({"get": "retrieve", "put": "update",
                                  "patch": "partial_update", "delete": "destroy"}),
         name="billitem-detail"),

    path("bills/<int:bill_pk>/stays/",
         BillStayViewSet.as_view({"post": "create"}), name="billstay-create"),
    path("bills/<int:bill_pk>/stays/<int:pk>/",
         BillStayViewSet.as_view({"patch": "partial_update", "delete": "destroy"}),
         name="billstay-detail"),

    # 集計・一覧（APIView / ListAPIView）
    path("cast-sales/",           CastSalesView.as_view(),          name="cast-sales"),
    path("cast-sales-summary/",   CastSalesSummaryView.as_view(),   name="cast-sales-summary"),
    path("cast-payouts/",         CastPayoutListView.as_view(),     name="cast-payouts"),
    path("cast-item-details/",    CastItemDetailView.as_view(),     name="cast-item-details"),
    path("cast-ranking/",         CastRankingView.as_view(),        name="cast-ranking"),
]
