import logging

from celery import shared_task

from . import services

logger = logging.getLogger(__name__)


@shared_task(name="apps.disputes.tasks.auto_escalate_overdue_disputes")
def auto_escalate_overdue_disputes() -> None:
    count = services.auto_escalate_overdue_disputes()
    if count:
        logger.info("Auto-escalated %d overdue dispute(s).", count)
