from django.apps import AppConfig

class BillingConfig(AppConfig):
    name = 'billing'

    def ready(self):
        # ここで signals を読み込む（下記で統合）
        import billing.signals  # noqa
