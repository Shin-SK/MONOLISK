# config/urls.py
from django.contrib import admin
from django.urls import include, path
from rest_framework import routers
from core import views

# ----- Router -----
router = routers.DefaultRouter()
router.register(r'stores',                views.StoreViewSet)
router.register(r'ranks',                 views.RankViewSet)
router.register(r'courses',               views.CourseViewSet)
router.register(r'rank-courses',          views.RankCourseViewSet)
router.register(r'options',               views.OptionViewSet)
router.register(r'group-option-prices',   views.GroupOptionPriceViewSet)
router.register(r'casts',                 views.CastViewSet)
router.register(r'cast-course-prices',    views.CastCoursePriceViewSet)
router.register(r'cast-options',          views.CastOptionViewSet)
router.register(r'drivers',               views.DriverViewSet)
router.register(r'customers',             views.CustomerViewSet)
router.register(r'reservations',          views.ReservationViewSet, basename='reservation')

# ----- urlpatterns -----
urlpatterns = [
    path('admin/', admin.site.urls),

    # API
    path('api/', include(router.urls)),
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),

    # allauth HTML ビューを使う場合だけ有効化
    # path('accounts/', include('allauth.urls')),
]
