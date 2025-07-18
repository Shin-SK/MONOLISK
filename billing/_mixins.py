# billing/mixins.py
from django.db import models

class OwnStoreQuerySetMixin:
    """
    request.user.store に紐づくレコードだけを返す共通 Mixin
    - モデル側に `store = ForeignKey(Store, …)` があることが前提
    """
    def get_queryset(self):
        qs = super().get_queryset()
        # staff / superuser は全件見えるようにしたいならここで分岐
        user = self.request.user
        if user.is_staff or user.is_superuser or user.store_id is None:
            return qs
        return qs.filter(store_id=user.store_id)
