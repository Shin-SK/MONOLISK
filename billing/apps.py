# billing/apps.py
from django.apps import AppConfig
class BillingConfig(AppConfig):
    name = 'billing'

    def ready(self):
        from django.contrib.auth import get_user_model
        from django.db.models.signals import post_save
        from .models import UserStore, Store

        User = get_user_model()

        def ensure_profile(sender, instance, created, **kwargs):
            if created and not hasattr(instance, 'store_profile'):
                # 既定店舗(先頭) を仮付与。必要なら None 可
                default_store = Store.objects.first()
                if default_store:
                    UserStore.objects.create(user=instance, store=default_store)

        post_save.connect(ensure_profile, sender=User)
