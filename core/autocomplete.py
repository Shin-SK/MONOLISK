# core/autocomplete.py
from dal import autocomplete
from django.urls import path
from .models import CastProfile

class CastByStore(autocomplete.Select2QuerySetView):
    """
    ?store=<ID> を受け取り、その店舗所属キャストだけ返す。
    store が無い時は全キャストを返す。
    """
    def get_queryset(self):
        qs = CastProfile.objects.all()
        store_id = self.forwarded.get('store')
        if store_id:
            qs = qs.filter(store_id=store_id)
        return qs

urlpatterns = [
    path('cast-by-store/', CastByStore.as_view(),
         name='cast-by-store'),
]
