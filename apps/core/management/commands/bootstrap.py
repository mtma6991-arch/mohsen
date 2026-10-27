from django.core.management.base import BaseCommand

from apps.core.bootstrap_data import ensure_admin_user, ensure_categories, ensure_examples


class Command(BaseCommand):
    help = "دسته‌ها، قالب‌ها و افزونه‌های نمونه را نصب می‌کند."

    def handle(self, *args, **options):
        created = ensure_categories()
        notes = ensure_examples()
        user, user_created = ensure_admin_user()
        if created:
            self.stdout.write(self.style.SUCCESS("دسته‌های تازه: " + ", ".join(created)))
        for line in notes:
            self.stdout.write(line)
        if user_created and user is not None:
            self.stdout.write(self.style.WARNING(f"کاربر مدیر ساخته شد: {user.username}"))
            if user.username == "admin":
                self.stdout.write(self.style.WARNING("رمز توسعه: admin12345  — فقط برای محیط توسعه."))
        self.stdout.write(self.style.SUCCESS("bootstrap تمام شد."))
