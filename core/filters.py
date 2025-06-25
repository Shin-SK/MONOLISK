# core/filters.py  ─── 修正版（タブインデント）

import django_filters as df
from django_filters import rest_framework as filters	# ★ 追加

from django.db.models import Q
from .models import Customer, Reservation, CastProfile


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

	def filter_store(self, qs, name, value):
		# value が '' や None のときはそのまま返す
		if not value:
			return qs
		return qs.filter(store_id=value)

	def filter_cast(self, qs, name, value):
		if not value:
			return qs
		return qs.filter(casts__cast_profile_id=value)

	class Meta:
		model  = Reservation
		fields = ['store', 'cast', 'date', 'customer']

class NumberInFilter(filters.BaseInFilter, filters.NumberFilter):
	"""カンマ区切りの id リストを受け取る汎用フィルタ"""
	pass

class CastProfileFilter(filters.FilterSet):
	store = NumberInFilter(field_name="store_id", lookup_expr="in")
	rank  = filters.NumberFilter(field_name="rank_id")
	q	 = filters.CharFilter(method="filter_name")

	def filter_name(self, qs, name, value):
		return qs.filter(stage_name__icontains=value)

	class Meta:
		model  = CastProfile
		fields = ["store", "rank"]
