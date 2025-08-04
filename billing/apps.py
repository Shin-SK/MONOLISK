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



class BillingConfig(AppConfig):
    name = 'billing'

    def ready(self):
        from django.db.models.signals import post_save
        from django.dispatch import receiver
        from django.contrib.auth import get_user_model
        from billing.models import Staff, Store

        User = get_user_model()

        @receiver(post_save, sender=User)
        def auto_create_staff(sender, instance, created, **kwargs):
            if instance.is_staff:
                staff, _ = Staff.objects.get_or_create(user=instance)
                # store_id があれば M2M に追加
                if getattr(instance, "store_id", None) and \
                   not staff.stores.filter(pk=instance.store_id).exists():
                    staff.stores.add(instance.store_id)
