from django.urls import path
from .views import ReservationSalesAPIView

urlpatterns = [
    path("", ReservationSalesAPIView.as_view(), name="reservation-sales"),  # URLの指定
]
