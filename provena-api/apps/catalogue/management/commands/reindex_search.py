"""Rebuild the Typesense product index from the active catalogue.

Run once after enabling search, or after a schema change:

    python manage.py reindex_search

Runs inline (not via Celery) so it is easy to invoke during deploys.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.catalogue.tasks import reindex_all_products


class Command(BaseCommand):
    help = "Reindex all active products into Typesense."

    def handle(self, *args, **options) -> None:
        if not settings.TYPESENSE_ENABLED:
            raise CommandError(
                "Search is disabled (TYPESENSE_HOST is not set); nothing to reindex."
            )
        count = reindex_all_products()
        self.stdout.write(self.style.SUCCESS(f"Reindexed {count} products into Typesense."))
