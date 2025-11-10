from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import StoreMembership, StoreRole

User = get_user_model()

class Command(BaseCommand):
    help = 'User.store を StoreMembership(is_primary) に移す初期化'

    def handle(self, *args, **opts):
        n = 0
        for u in User.objects.exclude(store__isnull=True):
            StoreMembership.objects.get_or_create(
                user=u, store=u.store, defaults={'role': StoreRole.MANAGER, 'is_primary': True}
            )
            n += 1
        self.stdout.write(self.style.SUCCESS(f'initialized: {n} memberships'))
