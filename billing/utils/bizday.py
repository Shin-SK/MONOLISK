# billing/utils/bizday.py
from __future__ import annotations
from datetime import datetime, time, timedelta, date as date_cls
from django.utils import timezone
from billing.models import Store

def get_business_window(business_date: date_cls, *, store_id: int):
    """
    営業日= [cutoff 当日 hh:00, 翌日 hh:00) の 1 日窓（TZ aware）を返す。
    """
    store = Store.objects.only("business_day_cutoff_hour").get(pk=store_id)
    cutoff = int(store.business_day_cutoff_hour or 0)

    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(business_date, time(hour=cutoff)), tz)
    end = start + timedelta(days=1)
    return start, end

def business_date_for(dt, *, store_id: int):
    """
    任意の日時 dt が属する営業日を返す（必要になったら使用）。
    """
    store = Store.objects.only("business_day_cutoff_hour").get(pk=store_id)
    cutoff = int(store.business_day_cutoff_hour or 0)

    tz = timezone.get_current_timezone()
    local = timezone.localtime(dt, tz)
    d = local.date()
    if local.time() < time(hour=cutoff):
        d = d - timedelta(days=1)
    return d
