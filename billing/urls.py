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
     CustomerViewSet, StoreNoticeViewSet, StoreSeatSettingViewSet, DiscountRuleViewSet, CastPayrollSummaryView, CastPayrollDetailView, CastPayrollDetailCSVView,
     CustomerTagViewSet,
)

from .api.pl_views import DailyPLAPIView, MonthlyPLAPIView, YearlyPLAPIView
from .kds_views import KDSTicketList, KDSTicketAck, KDSTicketReady, KDSReadyList, KDSTakeTicket, KDSTicketLongPoll, KDSReadyLongPoll, StaffList, KDSTakenTodayList
from .api_kds import order_events

router = DefaultRouter()
router.register(r"stores",               StoreViewSet,           basename="stores")
router.register(r"tables",               TableViewSet,           basename="tables")
router.register(r"item-masters",         ItemMasterViewSet,      basename="item-masters")
router.register(r"bills",                BillViewSet,            basename="bills")
router.register(r"casts",                CastViewSet,            basename="casts")
router.register(r"item-categories",      ItemCategoryViewSet,    basename="item-categories")
router.register(r"cast-shifts",          CastShiftViewSet,       basename="cast-shifts")
router.register(r"cast-daily-summaries", CastDailySummaryViewSet,basename="cast-daily-summaries")
router.register(r"staffs", StaffViewSet, basename="staffs")
router.register(r"staff-shifts",         StaffShiftViewSet,      basename="staff-shifts")
router.register(r"customers",            CustomerViewSet,        basename="customers")
router.register(r"store-notices",        StoreNoticeViewSet,     basename="store-notices")
router.register(r'store-seat-settings', StoreSeatSettingViewSet, basename='store-seat-settings')
router.register(r'discount-rules', DiscountRuleViewSet, basename='discount-rule')
router.register(r"customer-tags",       CustomerTagViewSet,     basename="customer-tags")


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
    
    # ★ 追加: P/L（Daily / Monthly / Yearly）
    path("pl/daily/",   DailyPLAPIView.as_view(),   name="pl-daily"),
    path("pl/monthly/", MonthlyPLAPIView.as_view(), name="pl-monthly"),
    path("pl/yearly/",  YearlyPLAPIView.as_view(),  name="pl-yearly"),
    
    # ★給与計算
    path("payroll/summary/", CastPayrollSummaryView.as_view(), name="payroll-summary"),
    path("payroll/casts/<int:cast_id>/", CastPayrollDetailView.as_view(), name="payroll-cast-detail"),
    path("payroll/casts/<int:cast_id>/export.csv", CastPayrollDetailCSVView.as_view(), name="payroll-cast-detail-csv"),
    
    path('kds/tickets/', KDSTicketList.as_view(), name='kds_ticket_list'),
    path('kds/tickets/<int:pk>/ack/', KDSTicketAck.as_view(), name='kds_ticket_ack'),
    path('kds/tickets/<int:pk>/ready/', KDSTicketReady.as_view(), name='kds_ticket_ready'),
    path('kds/ready-list/', KDSReadyList.as_view(), name='kds_ready_list'),
    path('kds/take/',       KDSTakeTicket.as_view(), name='kds_take'),
    path('kds/longpoll-tickets/', KDSTicketLongPoll.as_view(), name='kds_longpoll_tickets'),
    path('kds/longpoll-ready/',   KDSReadyLongPoll.as_view(),  name='kds_longpoll_ready'),
    path('kds/staffs/', StaffList.as_view(), name='kds_staff_list'),
    path('kds/taken-today/', KDSTakenTodayList.as_view(), name='kds_taken_today'),
    path('order-events/', order_events, name='order-events'),

]
