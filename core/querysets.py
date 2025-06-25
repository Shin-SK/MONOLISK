#core/querysets.py 
from django.contrib.postgres.aggregates import StringAgg
from django.db.models import F

Reservation.objects.annotate(
    cast_names=StringAgg(
        F('casts__cast_profile__stage_name'),
        delimiter=', ',
        distinct=True,          # 重複除外したい場合
    )
)
