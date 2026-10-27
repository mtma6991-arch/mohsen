import os

from django.core.management.base import BaseCommand, CommandError

from apps.core.bootstrap_data import ensure_admin_user


class Command(BaseCommand):
    help = "کاربر مدیر را از متغیرهای محیط می‌سازد یا رمزش را بازنشانی می‌کند."

    def handle(self, *args, **options):
        if not os.environ.get("MOHSEN_ADMIN_USER") or not os.environ.get("MOHSEN_ADMIN_PASSWORD"):
            raise CommandError("MOHSEN_ADMIN_USER و MOHSEN_ADMIN_PASSWORD لازم است.")
        user, created = ensure_admin_user()
        state = "ساخته شد" if created else "به‌روز شد"
        self.stdout.write(self.style.SUCCESS(f"کاربر {user.username} {state}."))
