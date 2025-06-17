import django_filters as df
from django.db.models import Q
from .models import Customer, Reservation

class CustomerFilter(df.FilterSet):
    # 部分一致 phone=123
    phone  = df.CharFilter(field_name='phone', lookup_expr='icontains')

    # 名前か電話で一括検索 ?search=abc
    search = df.CharFilter(method='name_or_phone')

    def name_or_phone(self, qs, name, value):
        return qs.filter(
            Q(name__icontains=value) | Q(phone__icontains=value)
        )

    class Meta:
        model  = Customer
        fields = ['name']   # 完全一致や将来追加分だけ入れる


class ReservationFilter(df.FilterSet):
    store = df.NumberFilter(field_name='store_id')
    cast  = df.NumberFilter(method='filter_cast')
    date  = df.DateFilter(field_name='start_at', lookup_expr='date')

    class Meta:
        model  = Reservation
        fields = ['store', 'cast', 'date']   # ← クエリ名を公開

    def filter_cast(self, qs, name, value):
        return qs.filter(casts__cast_profile_id=value)