import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def backup_database() -> str:
    """Periodic task: dump the database, upload it to S3/R2, and prune old backups."""
    from .backups import create_backup

    return create_backup()
