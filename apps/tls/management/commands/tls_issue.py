from django.core.management.base import BaseCommand, CommandError

from apps.tls.service import perform_issue


class Command(BaseCommand):
    help = "صدور یا تمدید گواهی یک دامنه. روی سرور با root اجرا می‌شود."

    def add_arguments(self, parser):
        parser.add_argument("--domain", required=True)
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        try:
            message = perform_issue(options["domain"], force=options["force"])
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(message)
