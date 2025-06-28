# core/filters.py  ─── 修正版（タブインデント）

import django_filters as df
from django_filters import rest_framework as filters	# ★ 追加

from django.db.models import Q
from .models import Customer, Reservation, CastProfile, ShiftPlan, ReservationDriver
from django.utils import timezone

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
	# ↓↓↓ 追加分 ↓↓↓
	from_date = df.DateFilter(
		field_name='start_at', lookup_expr='date__gte'
	)
	to_date   = df.DateFilter(
		field_name='start_at', lookup_expr='date__lte'
	)

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
		fields = ['store', 'cast', 'date', 'customer', 'from_date', 'to_date']

class NumberInFilter(filters.BaseInFilter, filters.NumberFilter):
	"""カンマ区切りの id リストを受け取る汎用フィルタ"""
	pass

class CastProfileFilter(filters.FilterSet):
	store = NumberInFilter(field_name="store_id", lookup_expr="in")
	rank  = filters.NumberFilter(field_name="rank_id")
	q	 = filters.CharFilter(method="filter_name")
	in_shift = filters.BooleanFilter(method="filter_in_shift")  # ★追加
	date	 = filters.DateFilter(method="filter_in_shift")	 # デフォルト今日

	def filter_name(self, qs, name, value):
		return qs.filter(stage_name__icontains=value)

	def filter_in_shift(self, qs, name, value):
		"""
		?in_shift=1 で当日出勤予定のキャストに限定
		日付は ?date=yyyy-mm-dd （未指定なら今日）
		"""
		if not value:
			return qs
		target = self.data.get("date") or timezone.localdate()
		return qs.filter(shift_plans__date=target)

	class Meta:
		model  = CastProfile
		fields = ["store", "rank", "in_shift", "date"]



class ShiftPlanFilter(filters.FilterSet):
	"""
	?date=YYYY-MM-DD（省略時は今日）
	?store=<id>	  （省略時は全店）
	"""
	date  = filters.DateFilter(field_name="date", lookup_expr="exact")
	store = NumberInFilter(field_name="store_id", lookup_expr="in")

	class Meta:
		model  = ShiftPlan
		fields = ["date", "store"]


class ReservationDriverFilter(filters.FilterSet):
	reservation = filters.NumberFilter(field_name="reservation_id")
	driver	  = filters.NumberFilter(field_name="driver_id")
	role		= filters.CharFilter(field_name="role")
	date		= filters.DateFilter(field_name="start_at", lookup_expr="date")

	class Meta:
		model  = ReservationDriver
		fields = ["reservation", "driver", "role", "date"]
