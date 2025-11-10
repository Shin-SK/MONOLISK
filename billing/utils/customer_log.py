from billing.models import CustomerLog   # utils はパッケージなので . で相対 import

def log_customer_change(user, customer, action, before, after):
    """
    顧客の create / update を履歴に残すヘルパ
    """
    CustomerLog.objects.create(
        customer=customer,
        user=user,
        action=action,
        payload={'before': before, 'after': after},
    )
