# billing/tests/test_payroll_summary.py
from decimal import Decimal
from datetime import date, datetime, time, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from django.utils import timezone

from billing.models import (
    Store, Table, ItemCategory, ItemMaster,
    Cast, Bill, BillItem, CastDailySummary, CastShift
)

User = get_user_model()


class PayrollReflectsEngineTests(TestCase):
    def setUp(self):
        self.ds = Store.objects.create(slug="dosukoi-asa", name="Dosukoi", service_rate=Decimal("0"), tax_rate=Decimal("0"))
        self.tb = Table.objects.create(store=self.ds, code="M01")
        self.ot = Store.objects.create(slug="other", name="Other", service_rate=Decimal("0"), tax_rate=Decimal("0"))
        self.tb_ot = Table.objects.create(store=self.ot, code="M01")

        self.cat_drink = ItemCategory.objects.create(
            code="drink", name="Drink",
            back_rate_free=Decimal("0.20"),
            back_rate_inhouse=Decimal("0.20"),
            back_rate_nomination=Decimal("0.20"),
            use_fixed_payout_free_in=False,
        )
        self.cat_bottle = ItemCategory.objects.create(
            code="bottle", name="Bottle",
            back_rate_free=Decimal("0.20"),
            back_rate_inhouse=Decimal("0.20"),
            back_rate_nomination=Decimal("0.20"),
            use_fixed_payout_free_in=True,  # dosukoi で固定500円の対象
        )

        self.drink_ds  = ItemMaster.objects.create(store=self.ds, code="DRINK-1",  name="Highball", price_regular=1000, category=self.cat_drink)
        self.bottle_ds = ItemMaster.objects.create(store=self.ds, code="BOTTLE-1", name="Shochu",   price_regular=6000, category=self.cat_bottle)

        self.user1   = User.objects.create_user(username="cast1", password="x")
        self.cast_ds = Cast.objects.create(user=self.user1, stage_name="Alice", store=self.ds)

        self.today  = date.today()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user1)

    def _close(self, bill: Bill):
        bill.close()  # closed_at と CastPayout を確定

    def _local_dt(self, d: date, hh=12, mm=0):
        tz = timezone.get_current_timezone()
        return timezone.make_aware(datetime.combine(d, time(hh, mm)), tz)

    def _upsert_summary(self, *, store: Store, cast: Cast, worked_min: int, payroll: int):
        rec, _ = CastDailySummary.objects.get_or_create(
            store=store, cast=cast, work_date=self.today,
            defaults=dict(worked_min=0, payroll=0,
                          sales_free=0, sales_in=0, sales_nom=0, sales_champ=0)
        )
        rec.worked_min = worked_min
        rec.payroll    = payroll
        rec.save(update_fields=["worked_min", "payroll"])

    def test_payroll_summary_reflects_engine_override(self):
        # DRINK(1000×1)=200, BOTTLE(6000×2)=500×2=1000 → commission=1200
        bill = Bill.objects.create(table=self.tb)
        BillItem.objects.create(bill=bill, item_master=self.drink_ds,  price=1000, qty=1, served_by_cast=self.cast_ds)
        BillItem.objects.create(bill=bill, item_master=self.bottle_ds, price=6000, qty=2, served_by_cast=self.cast_ds)
        self._close(bill)

        # 時給=3000（CastShiftに反映：summary/detail 両方が拾えるよう 当日正午で作成）
        ci = self._local_dt(self.today, 12, 0)
        co = ci + timedelta(minutes=180)
        CastShift.objects.create(
            store=self.ds, cast=self.cast_ds,
            clock_in=ci, clock_out=co,
            hourly_wage_snap=1000, worked_min=180, payroll_amount=3000,
        )
        # summary 用の CastDailySummary も整合
        self._upsert_summary(store=self.ds, cast=self.cast_ds, worked_min=180, payroll=3000)

        self.client.credentials(HTTP_X_STORE_ID=str(self.ds.id))
        res = self.client.get("/api/billing/payroll/summary/",
                              {"from": self.today.isoformat(), "to": self.today.isoformat()})
        self.assertEqual(res.status_code, 200, res.content)
        row = next(r for r in res.json() if r.get("stage_name") == "Alice")
        self.assertEqual(int(row["commission"]), 1200)
        self.assertEqual(int(row["hourly_pay"]), 3000)
        self.assertEqual(int(row["total"]),      4200)

    def test_payroll_detail_breakdown(self):
        # DRINK(1000×1)=200, BOTTLE(6000×1)=500 → commission=700
        bill = Bill.objects.create(table=self.tb)
        BillItem.objects.create(bill=bill, item_master=self.drink_ds,  price=1000, qty=1, served_by_cast=self.cast_ds)
        BillItem.objects.create(bill=bill, item_master=self.bottle_ds, price=6000, qty=1, served_by_cast=self.cast_ds)
        self._close(bill)

        # 時給=1000（CastShiftに入れる：detail はここだけを見る。※当日正午で固定）
        ci = self._local_dt(self.today, 12, 0)
        co = ci + timedelta(minutes=60)
        CastShift.objects.create(
            store=self.ds, cast=self.cast_ds,
            clock_in=ci, clock_out=co,
            hourly_wage_snap=1000, worked_min=60, payroll_amount=1000,
        )
        # summary 側の整合も一応合わせる（detailは参照しない）
        self._upsert_summary(store=self.ds, cast=self.cast_ds, worked_min=60, payroll=1000)

        self.client.credentials(HTTP_X_STORE_ID=str(self.ds.id))
        res = self.client.get(f"/api/billing/payroll/casts/{self.cast_ds.id}/",
                              {"from": self.today.isoformat(), "to": self.today.isoformat()})
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(int(body["totals"]["commission"]), 700)
        self.assertEqual(int(body["totals"]["hourly_pay"]), 1000)
        self.assertEqual(int(body["totals"]["total"]),      1700)