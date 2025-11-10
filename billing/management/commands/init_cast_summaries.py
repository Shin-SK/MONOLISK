# billing/management/commands/init_cast_summaries.py （抜粋・置換案）
# タブインデントで記載
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import localdate
from billing.models import Cast, CastDailySummary

class Command(BaseCommand):
	help = 'CastDailySummary が 1行も無いキャストだけに 0レコードを補完'

	def add_arguments(self, parser):
		parser.add_argument('--from', dest='d_from', type=str)
		parser.add_argument('--to',   dest='d_to',   type=str)

	def handle(self, *args, **opts):
		d_from = localdate() if not opts.get('d_from') else date.fromisoformat(opts['d_from'])
		d_to   = localdate() if not opts.get('d_to')   else date.fromisoformat(opts['d_to'])
		if d_from > d_to:
			self.stderr.write('invalid range'); return

		# 全期間でサマリー未保有のキャストだけ対象
		existing = CastDailySummary.objects.values_list('cast_id', flat=True).distinct()
		targets  = Cast.objects.exclude(id__in=existing).select_related('store')

		added = 0
		with transaction.atomic():
			cur = d_from
			while cur <= d_to:
				for cast in targets:
					if not cast.store_id:
						continue  # store 未設定はスキップ
					CastDailySummary.objects.get_or_create(
						cast=cast, store=cast.store, date=cur,
						defaults={'sales_total': 0, 'back_total': 0, 'nomination_count': 0}
					)
					added += 1
				cur += timedelta(days=1)

		self.stdout.write(self.style.SUCCESS(f'added: {added} rows'))
