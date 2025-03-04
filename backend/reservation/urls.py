from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReservationViewSet, UnpaidRoutesAPIView, CourseListAPIView, MenuListAPIView, DiscountListAPIView

router = DefaultRouter()
router.register(r"", ReservationViewSet)  # ✅ `reservations` に変更してURLを明確に

urlpatterns = [
    path("courses/", CourseListAPIView.as_view(), name="course-list"),
    path("menus/", MenuListAPIView.as_view(), name="menu-list"),
    path("discounts/", DiscountListAPIView.as_view(), name="discount-list"),
    path('drivers/<int:driver_id>/unpaid_routes/', UnpaidRoutesAPIView.as_view(), name='unpaid-routes'),
    path("", include(router.urls)),  # `/api/reservations/` で動作
]
