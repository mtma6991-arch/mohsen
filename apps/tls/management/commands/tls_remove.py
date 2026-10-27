from django.core.management.base import BaseCommand, CommandError

from apps.tls.service import perform_remove


class Command(BaseCommand):
    help = "برداشتن گواهی یک دامنه از nginx و از تمدید خودکار."

    def add_arguments(self, parser):
        parser.add_argument("--domain", required=True)

    def handle(self, *args, **options):
        try:
            message = perform_remove(options["domain"])
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(message)
