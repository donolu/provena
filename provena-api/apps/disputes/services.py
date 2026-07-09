"""Business logic for dispute lifecycle."""

import logging
import uuid
from datetime import timedelta

import boto3
import stripe
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.notifications.models import NotificationType
from apps.notifications.services import notify

from .models import (
    ALLOWED_ATTACHMENT_TYPES,
    ATTACHMENT_MAX_BYTES,
    FIXED_WINDOW_DAYS,
    FIXED_WINDOW_TYPES,
    Dispute,
    DisputeAttachment,
    DisputeEvent,
    DisputeEventType,
    DisputeMessage,
    DisputeOutcome,
    DisputeRefund,
    DisputeRefundStatus,
    DisputeStatus,
)

logger = logging.getLogger(__name__)


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
    return dispute


def auto_escalate_overdue_disputes() -> int:
    """Escalate all OPEN disputes past their response deadline. Returns count escalated."""
    from apps.accounts.models import Role, User

    overdue = Dispute.objects.filter(
        status=DisputeStatus.OPEN, response_deadline__lt=timezone.now()
    ).select_related("sub_order", "opened_by")

    count = 0
    for dispute in overdue:
        with transaction.atomic():
            dispute.status = DisputeStatus.ESCALATED
            dispute.save(update_fields=["status"])
            system_user = dispute.opened_by  # use opener as author for the audit event
            DisputeEvent.objects.create(
                dispute=dispute,
                author=system_user,
                event_type=DisputeEventType.AUTO_ESCALATED,
                body="Automatically escalated: response deadline exceeded.",
            )
            for admin in User.objects.filter(role=Role.ADMIN):
                notify(
                    recipient=admin,
                    title="Dispute auto-escalated",
                    body=(
                        f"Dispute on order {dispute.sub_order} was automatically escalated "
                        "because the response deadline passed with no reply."
                    ),
                    notification_type=NotificationType.GENERAL,
                    data={"dispute_id": str(dispute.id)},
                )
            count += 1
    return count


def resolve_dispute(
    dispute: Dispute,
    admin,
    outcome: str,
    outcome_amount_pence: int | None,
    outcome_notes: str,
) -> Dispute:
    refund_outcomes = {DisputeOutcome.FULL_REFUND, DisputeOutcome.PARTIAL_REFUND}

    # Issue the Stripe refund BEFORE opening a DB transaction so that a network
    # error never causes a partial rollback of already-committed dispute state.
    # The idempotency key makes retries safe: Stripe returns the same refund on
    # duplicate requests for the same dispute.
    # stripe_refund_data carries (stripe_refund_id, amount_pence) when a refund
    # was issued; None otherwise. The tuple keeps both fields type-narrowed to int/str.
    stripe_refund_data: tuple[str, int] | None = None
    if outcome in refund_outcomes:
        if outcome == DisputeOutcome.FULL_REFUND:
            amount_pence: int = int(dispute.sub_order.subtotal * 100)
        else:
            if outcome_amount_pence is None:
                raise ValueError("outcome_amount_pence is required for PARTIAL_REFUND outcomes.")
            amount_pence = outcome_amount_pence

        stripe.api_key = settings.STRIPE_SECRET_KEY
        payment_intent_id = dispute.sub_order.order.payment.stripe_payment_intent_id
        stripe_refund = stripe.Refund.create(
            payment_intent=payment_intent_id,
            amount=amount_pence,
            idempotency_key=f"dispute-refund-{dispute.id}",
        )
        stripe_refund_data = (stripe_refund.id, amount_pence)
        logger.info(
            "Auto-triggered Stripe refund %s (%dp) for dispute %s",
            stripe_refund_data[0],
            stripe_refund_data[1],
            dispute.id,
        )

    with transaction.atomic():
        if stripe_refund_data is not None:
            stripe_refund_id, refund_amount_pence = stripe_refund_data
            refund_record = DisputeRefund.objects.create(
                dispute=dispute,
                sub_order=dispute.sub_order,
                stripe_refund_id=stripe_refund_id,
                amount_pence=refund_amount_pence,
                status=DisputeRefundStatus.PENDING,
            )
            refund_record_id = str(refund_record.id)
            transaction.on_commit(
                lambda: notify(
                    recipient=dispute.opened_by,
                    title="Refund initiated",
                    body=f"A refund of £{refund_amount_pence / 100:.2f} has been initiated for your dispute.",
                    notification_type=NotificationType.GENERAL,
                    data={"dispute_id": str(dispute.id), "refund_id": refund_record_id},
                )
            )

        dispute.status = DisputeStatus.RESOLVED
        dispute.outcome = outcome
        dispute.outcome_amount_pence = outcome_amount_pence
        dispute.outcome_notes = outcome_notes
        dispute.resolved_at = timezone.now()

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
        outcome_display = dispute.get_outcome_display()
        for recipient in (dispute.opened_by, dispute.respondent):
            transaction.on_commit(
                lambda r=recipient: notify(
                    recipient=r,
                    title="Dispute resolved",
                    body=f"The dispute on order {dispute.sub_order} has been resolved: {outcome_display}.",
                    notification_type=NotificationType.GENERAL,
                    data={"dispute_id": str(dispute.id), "outcome": outcome},
                )
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
    """Manually record a Stripe refund that was issued outside the auto-flow."""
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
        body=f"Refund of {amount_pence}p recorded (Stripe refund {stripe_refund_id}).",
    )
    notify(
        recipient=dispute.opened_by,
        title="Refund initiated",
        body=f"A refund of £{amount_pence / 100:.2f} has been initiated for your dispute.",
        notification_type=NotificationType.GENERAL,
        data={"dispute_id": str(dispute.id), "refund_id": str(refund.id)},
    )
    return refund


# ---------------------------------------------------------------------------
# Message thread (#38)
# ---------------------------------------------------------------------------


def post_message(dispute: Dispute, author, body: str) -> DisputeMessage:
    message = DisputeMessage.objects.create(dispute=dispute, author=author, body=body)
    # Notify the other party and any admins.
    from apps.accounts.models import Role, User

    recipients = set()
    if author.id != dispute.opened_by_id:
        recipients.add(dispute.opened_by_id)
    if author.id != dispute.respondent_id:
        recipients.add(dispute.respondent_id)
    admin_ids = User.objects.filter(role=Role.ADMIN).values_list("id", flat=True)
    for aid in admin_ids:
        if aid != author.id:
            recipients.add(aid)

    for user in User.objects.filter(id__in=recipients):
        notify(
            recipient=user,
            title="New message on dispute",
            body=f"{author.email} sent a message on dispute for order {dispute.sub_order}.",
            notification_type=NotificationType.GENERAL,
            data={"dispute_id": str(dispute.id)},
        )
    return message


# ---------------------------------------------------------------------------
# File evidence uploads (#37)
# ---------------------------------------------------------------------------


def generate_attachment_upload_url(
    dispute: Dispute,
    uploaded_by,
    filename: str,
    content_type: str,
    size_bytes: int,
) -> tuple[DisputeAttachment, str]:
    """
    Creates a DisputeAttachment record and returns a pre-signed S3 PUT URL.
    Raises ValueError for disallowed content types or oversized files.
    """
    if content_type not in ALLOWED_ATTACHMENT_TYPES:
        raise ValueError(f"File type '{content_type}' is not permitted.")
    if size_bytes > ATTACHMENT_MAX_BYTES:
        raise ValueError(f"File exceeds the 10 MB limit ({size_bytes} bytes).")

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    file_key = f"dispute-attachments/{dispute.id}/{uuid.uuid4()}.{ext}"

    attachment = DisputeAttachment.objects.create(
        dispute=dispute,
        uploaded_by=uploaded_by,
        filename=filename,
        content_type=content_type,
        file_key=file_key,
        size_bytes=size_bytes,
    )
    DisputeEvent.objects.create(
        dispute=dispute,
        author=uploaded_by,
        event_type=DisputeEventType.ATTACHMENT,
        body=filename,
    )

    s3 = boto3.client(
        "s3",
        region_name=settings.AWS_S3_REGION_NAME,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        endpoint_url=getattr(settings, "AWS_S3_ENDPOINT_URL", None),
    )
    upload_url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
            "Key": file_key,
            "ContentType": content_type,
        },
        ExpiresIn=900,  # 15 minutes
    )
    return attachment, upload_url


def attachment_public_url(attachment: DisputeAttachment) -> str:
    """Return a time-limited download URL for an attachment."""
    s3 = boto3.client(
        "s3",
        region_name=settings.AWS_S3_REGION_NAME,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        endpoint_url=getattr(settings, "AWS_S3_ENDPOINT_URL", None),
    )
    url: str = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": attachment.file_key},
        ExpiresIn=3600,
    )
    return url
