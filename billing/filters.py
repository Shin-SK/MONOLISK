# billing/filters.py

from django_filters import rest_framework as filters
from .models import CastPayout, BillItem, Bill


class BillFilter(filters.FilterSet):
    """Phase 2: Bill filtering with M2M table support"""
    table = filters.NumberFilter(field_name="table_id")           # legacy互換
    table_atom = filters.NumberFilter(field_name="tables__id")    # M2M
    
    class Meta:
        model = Bill
        fields = ['table', 'table_atom']

class CastPayoutFilter(filters.FilterSet):
    year  = filters.NumberFilter(method='filter_year')
    month = filters.NumberFilter(method='filter_month')

    from_date = filters.DateFilter(field_name='bill__closed_at', lookup_expr='gte')
    to_date   = filters.DateFilter(field_name='bill__closed_at', lookup_expr='lte')

    def filter_year(self, qs, name, value):
        return qs.filter(bill__closed_at__year=value)

    def filter_month(self, qs, name, value):
        return qs.filter(bill__closed_at__month=value)

    class Meta:
        model  = CastPayout
        fields = ['year', 'month', 'from_date', 'to_date']


class CastItemFilter(filters.FilterSet):
	from_date = filters.DateFilter(field_name='bill__closed_at', lookup_expr='gte')
	to_date   = filters.DateFilter(field_name='bill__closed_at', lookup_expr='lte')
	cast      = filters.NumberFilter(field_name='served_by_cast_id')

	class Meta:
		model  = BillItem              # ← ここが違う
		fields = ['from_date', 'to_date', 'cast']
