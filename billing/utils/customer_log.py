from billing.models import CustomerLog   # utils はパッケージなので . で相対 import
from django.core.serializers.json import DjangoJSONEncoder
import json

def log_customer_change(user, customer, action, before, after):
    """
    顧客の create / update を履歴に残すヘルパ
    """
    # datetime を JSON シリアライズ可能な形式に変換
    payload = {
        'before': json.loads(json.dumps(before, cls=DjangoJSONEncoder)),
        'after': json.loads(json.dumps(after, cls=DjangoJSONEncoder)),
    }
    
    CustomerLog.objects.create(
        customer=customer,
        user=user,
        action=action,
        payload=payload,
    )
