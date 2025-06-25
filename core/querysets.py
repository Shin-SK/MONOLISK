# core/querysets.py
from django.db.models import QuerySet, F
from django.contrib.postgres.aggregates import StringAgg


class ReservationQuerySet(QuerySet):
    """予約一覧に『キャスト名まとめ』を付ける専用 QuerySet"""

    def with_cast_names(self):
        return self.annotate(
            # 例）"秋月理央奈, るな" と 1 つの文字列で返す
            cast_names=StringAgg(
                F("casts__cast_profile__stage_name"),
                delimiter=", ",
                distinct=True,      # 同じキャストが重複しても 1 つに
            )
        )
