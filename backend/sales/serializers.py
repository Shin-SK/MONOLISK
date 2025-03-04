from rest_framework import serializers
from reservation.models import Reservation

class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ['id', 'customer_name', 'start_time', 'course', 'menus', 'store', 'cast', 'driver', 'cast_received', 'driver_received', 'store_received']
