from django.core.management.base import BaseCommand, CommandError

from apps.tls.service import perform_maintain


class Command(BaseCommand):
    help = "تمدید گواهی‌های نزدیک به انقضا و صدور دوباره برای دامنه‌های بدون گواهی."

    def handle(self, *args, **options):
        try:
            message = perform_maintain()
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(message)
