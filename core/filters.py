# core/filters.py  ─── 修正版（タブインデント）

import django_filters as df
from django_filters import rest_framework as filters	# ★ 追加

from django.db.models import Q
from .models import Customer, Reservation


class CustomerFilter(df.FilterSet):
	phone	= df.CharFilter(field_name='phone', lookup_expr='icontains')
	search   = df.CharFilter(method='name_or_phone')

	def name_or_phone(self, qs, name, value):
		return qs.filter(
			Q(name__icontains=value) | Q(phone__icontains=value)
		)

	class Meta:
		model  = Customer
		fields = ['name']


class ReservationFilter(df.FilterSet):
	store	 = df.NumberFilter(field_name='store_id')
	cast	  = df.NumberFilter(method='filter_cast')
	date	  = df.DateFilter(field_name='start_at', lookup_expr='date')
	customer  = filters.NumberFilter()					# ★ ここで filters を使用

	class Meta:
		model  = Reservation
		fields = ['store', 'cast', 'date', 'customer']

	def filter_cast(self, qs, name, value):
		return qs.filter(casts__cast_profile_id=value)
