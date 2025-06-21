# core/autocomplete.py
from dal import autocomplete
from django.urls import path
from .models import CastProfile, Customer


class CastByStore(autocomplete.Select2QuerySetView):
    """
    ?store=<ID> を受け取り、その店舗所属キャストだけ返す。
    store が無い時は全キャストを返す。
    """
    def get_queryset(self):
        qs = CastProfile.objects.all()
        store_id = self.forwarded.get('store')
        if store_id:
            qs = qs.filter(store_id=store_id)
        return qs

urlpatterns = [
    path('cast-by-store/', CastByStore.as_view(),
         name='cast-by-store'),
]



class CustomerByPhone(autocomplete.Select2QuerySetView):
    """
    入力値（term）は電話番号として部分一致検索。
    見つからなければ その term で新規 Customer を create_field='phone' で作成可。
    """
    create_field = 'phone'          # ★ ここが “無ければ作る” スイッチ
    create_value = lambda self, term: term   # phone にそのまま入れる

    def get_queryset(self):
        qs = Customer.objects.all()
        if self.q:
            qs = qs.filter(phone__icontains=self.q)
        return qs

    def get_result_label(self, customer):    # 下に表示するラベル
        return f'{customer.name or "(新規)"} – {customer.phone}'



urlpatterns = [
    path("cast-by-store/", CastByStore.as_view(),   name="cast-by-store"),
    path("customer-phone/", CustomerByPhone.as_view(), name="customer-by-phone"),
]