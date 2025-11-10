# billing/management/commands/sync_staff_from_users.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from billing.models import Staff, Store   # Store は無くても可

User = get_user_model()

class Command(BaseCommand):
    help = "is_staff=True の User 全員に Staff 行を作成（重複はスキップ）"

    def handle(self, *args, **opts):
        created = 0
        for u in User.objects.filter(is_staff=True):
            staff, new = Staff.objects.get_or_create(user=u)
            # User が store_id を持つ場合、所属登録
            if getattr(u, "store_id", None):
                staff.stores.add(u.store_id)
            if new:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"created: {created}"))
