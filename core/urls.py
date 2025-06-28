from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from . import views
from .views_pricing import PricingAPIView
from .views import SalesSummary

router = DefaultRouter()
router.register(r'stores',               views.StoreViewSet)
router.register(r'ranks',                views.RankViewSet)
router.register(r'courses',              views.CourseViewSet)
router.register(r'rank-courses',         views.RankCourseViewSet)
router.register(r'options',              views.OptionViewSet)
router.register(r'group-option-prices',  views.GroupOptionPriceViewSet)
router.register(r'casts',                views.CastViewSet)
router.register(r'cast-course-prices',   views.CastCoursePriceViewSet)
router.register(r'cast-options',         views.CastOptionViewSet)
router.register(r'drivers',              views.DriverViewSet)
router.register(r'customers',            views.CustomerViewSet, basename='customers')
router.register(r'reservations',         views.ReservationViewSet, basename='reservations')
router.register(r'cast-profiles',        views.CastProfileViewSet, basename='cast-profiles')
router.register(r"shift-plans",       views.ShiftPlanViewSet)
router.register(r"shift-attendances", views.ShiftAttendanceViewSet, basename="shiftattendance")
router.register(r"reservation-drivers", views.ReservationDriverViewSet)

# ── Customer → Addresses のネスト ──
addresses_router = NestedDefaultRouter(router, r'customers', lookup='customer')
addresses_router.register(r'addresses', views.CustomerAddressViewSet, basename='customer-addresses')

urlpatterns = [
	*router.urls,
	*addresses_router.urls,
	path('pricing/', PricingAPIView.as_view(), name='pricing'),
	path('sales/summary/', SalesSummary.as_view(), name='sales-summary'),
]
