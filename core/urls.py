from django.urls import path, include
from rest_framework import routers
from core import views

router = routers.DefaultRouter()
router.register(r'reservations', views.ReservationViewSet, basename='reservation')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/auth/', include('dj_rest_auth.urls')),            # login/logout
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
]
