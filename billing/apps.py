# billing/apps.py
from django.apps import AppConfig

class BillingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'billing'

    def ready(self):
        # signals の登録（アプリ起動時に一度だけ）
        from . import signals  # noqa: F401
        import billing.models_profile
        from billing.payroll.engines import _autodiscover  # noqa
        _autodiscover()