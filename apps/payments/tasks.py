import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def trigger_payout(self, payout_id: str) -> dict:
    """Initiate a Stripe Connect transfer for a single Payout record.

    Retries up to 3 times with 60-second back-off on transient failures.
    """
    from apps.payments.models import Payout, PayoutStatus
    from apps.payments.services import process_payout

    try:
        payout = Payout.objects.select_related("supplier", "sub_order__order__payment").get(
            id=payout_id
        )
    except Payout.DoesNotExist:
        logger.error("trigger_payout: payout %s not found", payout_id)
        return {"status": "not_found", "payout_id": payout_id}

    if payout.status != PayoutStatus.PENDING:
        logger.info(
            "trigger_payout: payout %s already in status %s, skipping",
            payout_id,
            payout.status,
        )
        return {"status": "skipped", "payout_id": payout_id}

    if not payout.supplier.stripe_account_id or not payout.supplier.stripe_onboarding_complete:
        logger.warning(
            "trigger_payout: supplier '%s' has not completed Stripe onboarding; skipping",
            payout.supplier.business_name,
        )
        return {"status": "no_stripe_account", "payout_id": payout_id}

    try:
        payout = process_payout(payout)
        logger.info(
            "trigger_payout: payout %s processed, transfer %s",
            payout_id,
            payout.stripe_transfer_id,
        )
        return {
            "status": "processed",
            "payout_id": payout_id,
            "transfer": payout.stripe_transfer_id,
        }
    except Exception as exc:
        logger.exception("trigger_payout: error processing payout %s", payout_id)
        raise self.retry(exc=exc) from exc
