"""Business logic for dispute lifecycle."""

from datetime import timedelta

from django.utils import timezone

from apps.notifications.models import NotificationType
from apps.notifications.services import notify

from .models import (
    FIXED_WINDOW_DAYS,
    FIXED_WINDOW_TYPES,
    Dispute,
    DisputeEvent,
    DisputeEventType,
    DisputeOutcome,
    DisputeRefund,
    DisputeRefundStatus,
    DisputeStatus,
)


def _resolve_window_days(sub_order, dispute_type: str) -> int:
    if dispute_type in FIXED_WINDOW_TYPES:
        return FIXED_WINDOW_DAYS
    try:
        first_item = sub_order.items.select_related("variant__product__category").first()
        cat = first_item.variant.product.category if first_item else None
        return cat.dispute_window_days if cat else 3
    except Exception:
        return 3


def open_dispute(
    sub_order,
    opened_by,
    respondent,
    dispute_type: str,
    description: str,
    resolution_requested: str,
) -> Dispute:
    window_days = _resolve_window_days(sub_order, dispute_type)
    deadline = sub_order.order.created_at + timedelta(days=window_days)

    dispute = Dispute.objects.create(
        sub_order=sub_order,
        opened_by=opened_by,
        respondent=respondent,
        dispute_type=dispute_type,
        description=description,
        resolution_requested=resolution_requested,
        response_deadline=deadline,
        payout_held=True,
    )
    DisputeEvent.objects.create(
        dispute=dispute,
        author=opened_by,
        event_type=DisputeEventType.OPENED,
        body=description,
    )
    notify(
        recipient=respondent,
        title="A dispute has been opened",
        body=f"A dispute has been raised against sub-order {sub_order}. Please respond.",
        notification_type=NotificationType.GENERAL,
        data={"dispute_id": str(dispute.id)},
    )
    return dispute


def respond_to_dispute(dispute: Dispute, respondent, body: str) -> Dispute:
    dispute.status = DisputeStatus.RESPONDENT_REPLIED
    dispute.save(update_fields=["status"])
    DisputeEvent.objects.create(
        dispute=dispute,
        author=respondent,
        event_type=DisputeEventType.RESPONDED,
        body=body,
    )
    notify(
        recipient=dispute.opened_by,
        title="Dispute response received",
        body=f"The respondent has replied to your dispute on order {dispute.sub_order}.",
        notification_type=NotificationType.GENERAL,
        data={"dispute_id": str(dispute.id)},
    )
    return dispute


def escalate_dispute(dispute: Dispute, escalated_by, body: str = "") -> Dispute:
    dispute.status = DisputeStatus.ESCALATED
    dispute.save(update_fields=["status"])
    DisputeEvent.objects.create(
        dispute=dispute,
        author=escalated_by,
        event_type=DisputeEventType.ESCALATED,
        body=body,
    )
    # Notify admins via a generic recipient approach; actual admin notification
    # is handled at the view layer where the admin user list is accessible.
    return dispute


def resolve_dispute(
    dispute: Dispute,
    admin,
    outcome: str,
    outcome_amount_pence: int | None,
    outcome_notes: str,
) -> Dispute:
    dispute.status = DisputeStatus.RESOLVED
    dispute.outcome = outcome
    dispute.outcome_amount_pence = outcome_amount_pence
    dispute.outcome_notes = outcome_notes
    dispute.resolved_at = timezone.now()

    # Release payout hold for supplier-favoured outcomes; keep held for refund outcomes.
    if outcome in (DisputeOutcome.REJECTED, DisputeOutcome.WITHDRAWN):
        dispute.payout_held = False

    dispute.save(
        update_fields=[
            "status",
            "outcome",
            "outcome_amount_pence",
            "outcome_notes",
            "resolved_at",
            "payout_held",
        ]
    )
    DisputeEvent.objects.create(
        dispute=dispute,
        author=admin,
        event_type=DisputeEventType.RESOLVED,
        body=outcome_notes,
    )
    for recipient in (dispute.opened_by, dispute.respondent):
        notify(
            recipient=recipient,
            title="Dispute resolved",
            body=f"The dispute on order {dispute.sub_order} has been resolved: {dispute.get_outcome_display()}.",
            notification_type=NotificationType.GENERAL,
            data={"dispute_id": str(dispute.id), "outcome": outcome},
        )
    return dispute


def close_dispute(dispute: Dispute, closed_by, body: str = "") -> Dispute:
    dispute.status = DisputeStatus.CLOSED
    dispute.payout_held = False
    dispute.save(update_fields=["status", "payout_held"])
    DisputeEvent.objects.create(
        dispute=dispute,
        author=closed_by,
        event_type=DisputeEventType.CLOSED,
        body=body,
    )
    return dispute


def trigger_refund(
    dispute: Dispute, admin, stripe_refund_id: str, amount_pence: int
) -> DisputeRefund:
    """Create a DisputeRefund record after admin has called Stripe."""
    refund = DisputeRefund.objects.create(
        dispute=dispute,
        sub_order=dispute.sub_order,
        stripe_refund_id=stripe_refund_id,
        amount_pence=amount_pence,
        status=DisputeRefundStatus.PENDING,
    )
    DisputeEvent.objects.create(
        dispute=dispute,
        author=admin,
        event_type=DisputeEventType.ADMIN_NOTE,
        body=f"Refund of {amount_pence}p triggered (Stripe refund {stripe_refund_id}).",
    )
    notify(
        recipient=dispute.opened_by,
        title="Refund initiated",
        body=f"A refund of £{amount_pence / 100:.2f} has been initiated for your dispute.",
        notification_type=NotificationType.GENERAL,
        data={"dispute_id": str(dispute.id), "refund_id": str(refund.id)},
    )
    return refund
