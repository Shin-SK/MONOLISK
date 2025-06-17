from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework import routers
from django.views.generic import TemplateView
from . import views   # ← ViewSet 群を import
from .views_pricing import PricingAPIView

router = DefaultRouter()
router.register(r"stores",               views.StoreViewSet)
router.register(r"ranks",                views.RankViewSet)
router.register(r"courses",              views.CourseViewSet)
router.register(r"rank-courses",         views.RankCourseViewSet)
router.register(r"options",              views.OptionViewSet)
router.register(r"group-option-prices",  views.GroupOptionPriceViewSet)
router.register(r"casts",                views.CastViewSet)
router.register(r"cast-course-prices",   views.CastCoursePriceViewSet)
router.register(r"cast-options",         views.CastOptionViewSet)
router.register(r"drivers",              views.DriverViewSet)
router.register(r"customers",            views.CustomerViewSet)
router.register(r"reservations",         views.ReservationViewSet, basename="reservation")
router.register(r'cast-profiles', views.CastProfileViewSet, basename='cast-profile')

urlpatterns = router.urls

urlpatterns += [
    path("pricing/", PricingAPIView.as_view(), name="pricing"),
]