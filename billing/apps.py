# billing/apps.py
from django.apps import AppConfig

class BillingConfig(AppConfig):
    name = 'billing'

    def ready(self):
        from django.contrib.auth import get_user_model
        from django.db.models.signals import post_save
        from .models import Store

        User = get_user_model()

        def set_default_store(sender, instance, created, **kwargs):
            if created and instance.store_id is None:
                default = Store.objects.first()
                if default:
                    instance.store = default
                    instance.save(update_fields=['store'])

        post_save.connect(set_default_store, sender=User)
