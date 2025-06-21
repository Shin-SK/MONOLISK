from django import template
from core.models import Reservation

register = template.Library()

@register.simple_tag
def recent_reservations(limit=30):
    """
    開始日時が新しい順に ``limit`` 件だけ返す
    {% recent_reservations as recents %}
    """
    return Reservation.objects.order_by('-start_at')[:limit]
