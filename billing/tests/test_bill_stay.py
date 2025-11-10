# billing/tests/test_bill_stay.py
import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_create_stay(api_client, bill, cast, staff_user):
    # 認証
    api_client.force_authenticate(staff_user)

    # ViewSet の basename = 'bill-stays' なので
    url = reverse('bill-stays-list', kwargs={'bill_pk': bill.id})
    payload = {'cast_id': cast.id, 'stay_type': 'free'}

    res = api_client.post(url, payload, format='json')

    assert res.status_code == 201, res.data           # 失敗時にレスポンス表示
    # DB まで検証するなら
    from billing.models import BillCastStay
    assert BillCastStay.objects.filter(bill=bill, cast=cast, stay_type='free').exists()
