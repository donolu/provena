from django.core.management.base import BaseCommand

from apps.ops.backups import create_backup


class Command(BaseCommand):
    help = "Dump the database, gzip it, upload to S3/R2, and prune old backups."

    def handle(self, *args, **options) -> None:
        key = create_backup()
        self.stdout.write(self.style.SUCCESS(f"Database backup uploaded: {key}"))
