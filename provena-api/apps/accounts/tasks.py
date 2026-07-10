import hashlib
import secrets
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.notifications.email_service import send_data_export_ready_email


@shared_task
def generate_data_export(export_id: str) -> None:
    from .models import DataExportRequest, DataExportStatus

    try:
        export = DataExportRequest.objects.select_related("user").get(pk=export_id)
    except DataExportRequest.DoesNotExist:
        return

    export.status = DataExportStatus.PROCESSING
    export.save(update_fields=["status"])

    try:
        payload = _collect_user_data(export.user)

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = timezone.now() + timedelta(hours=DataExportRequest.DOWNLOAD_TTL_HOURS)

        export.payload = payload
        export.token_hash = token_hash
        export.expires_at = expires_at
        export.status = DataExportStatus.COMPLETED
        export.completed_at = timezone.now()
        export.save(update_fields=["payload", "token_hash", "expires_at", "status", "completed_at"])

        send_data_export_ready_email(export.user, token)

    except Exception:
        export.status = DataExportStatus.FAILED
        export.payload = None
        export.token_hash = ""  # nosec B105
        export.expires_at = None
        export.save(update_fields=["status", "payload", "token_hash", "expires_at"])
        raise


@shared_task
def purge_expired_exports() -> None:
    """Delete payload from completed exports whose download window has closed."""
    from .models import DataExportRequest, DataExportStatus

    DataExportRequest.objects.filter(
        status=DataExportStatus.COMPLETED,
        expires_at__lt=timezone.now(),
    ).update(payload=None, token_hash="")  # nosec B106


def _collect_user_data(user) -> dict:
    from apps.disputes.models import Dispute, DisputeEvent, DisputeMessage
    from apps.marketplace.models import Review, WishlistItem
    from apps.notifications.models import Notification, NotificationPreference
    from apps.orders.models import Order

    profile = {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }

    addresses = [
        {
            "id": str(a.id),
            "label": a.label,
            "full_name": a.full_name,
            "line1": a.line1,
            "line2": a.line2,
            "city": a.city,
            "postcode": a.postcode,
            "country": a.country,
            "is_default": a.is_default,
            "created_at": a.created_at.isoformat(),
        }
        for a in user.addresses.all()
    ]

    orders = []
    for order in (
        Order.objects.filter(buyer=user)
        .prefetch_related("sub_orders__items", "sub_orders__supplier", "sub_orders__returns")
        .select_related("payment")
    ):
        order_dict: dict = {
            "reference": order.reference,
            "status": order.status,
            "total_amount": str(order.total_amount),
            "shipping": {
                "name": order.shipping_name,
                "line1": order.shipping_line1,
                "line2": order.shipping_line2,
                "city": order.shipping_city,
                "postcode": order.shipping_postcode,
                "country": order.shipping_country,
            },
            "notes": order.notes,
            "created_at": order.created_at.isoformat(),
            "sub_orders": [
                {
                    "id": str(sub.id),
                    "supplier": sub.supplier.business_name,
                    "status": sub.status,
                    "subtotal": str(sub.subtotal),
                    "tracking_number": sub.tracking_number,
                    "items": [
                        {
                            "product": item.product_name,
                            "quantity": item.quantity,
                            "unit_price": str(item.unit_price),
                        }
                        for item in sub.items.all()
                    ],
                    "returns": [
                        {
                            "id": str(r.id),
                            "reason": r.reason,
                            "status": r.status,
                            "created_at": r.created_at.isoformat(),
                        }
                        for r in sub.returns.filter(raised_by=user)
                    ],
                }
                for sub in order.sub_orders.all()
            ],
        }
        try:
            order_dict["payment"] = {
                "status": order.payment.status,
                "amount": str(order.payment.amount),
                "currency": order.payment.currency,
            }
        except Exception:  # noqa: S110  # nosec B110
            pass
        orders.append(order_dict)

    wishlist = [
        {
            "id": str(w.id),
            "variant_sku": w.variant.sku,
            "product_name": w.variant.product.name,
            "added_at": w.added_at.isoformat(),
        }
        for w in WishlistItem.objects.filter(buyer=user).select_related("variant__product")
    ]

    reviews = [
        {
            "id": str(r.id),
            "variant_sku": r.variant.sku,
            "rating": r.rating,
            "title": r.title,
            "body": r.body,
            "is_verified_purchase": r.is_verified_purchase,
            "is_approved": r.is_approved,
            "created_at": r.created_at.isoformat(),
        }
        for r in Review.objects.filter(reviewer=user).select_related("variant")
    ]

    notifications = [
        {
            "id": str(n.id),
            "type": n.notification_type,
            "title": n.title,
            "body": n.body,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
        }
        for n in Notification.objects.filter(recipient=user)
    ]

    try:
        prefs = NotificationPreference.objects.get(user=user)
        notification_preferences = {
            "email_order_placed": prefs.email_order_placed,
            "email_order_dispatched": prefs.email_order_dispatched,
            "email_new_order": prefs.email_new_order,
            "email_payout_received": prefs.email_payout_received,
        }
    except NotificationPreference.DoesNotExist:
        notification_preferences = None

    all_disputes = Dispute.objects.filter(opened_by=user) | Dispute.objects.filter(respondent=user)
    disputes = []
    for d in (
        all_disputes.distinct()
        .prefetch_related("messages", "events")
        .select_related("opened_by", "respondent")
    ):
        disputes.append(
            {
                "id": str(d.id),
                "sub_order": str(d.sub_order_id),
                "role": "opener" if d.opened_by_id == user.pk else "respondent",
                "type": d.dispute_type,
                "status": d.status,
                "description": d.description,
                "resolution_requested": d.resolution_requested,
                "outcome": d.outcome,
                "opened_at": d.opened_at.isoformat(),
                "resolved_at": d.resolved_at.isoformat() if d.resolved_at else None,
                "messages": [
                    {
                        "id": str(m.id),
                        "body": m.body,
                        "created_at": m.created_at.isoformat(),
                    }
                    for m in DisputeMessage.objects.filter(dispute=d, author=user)
                ],
                "events": [
                    {
                        "id": str(e.id),
                        "event_type": e.event_type,
                        "body": e.body,
                        "created_at": e.created_at.isoformat(),
                    }
                    for e in DisputeEvent.objects.filter(dispute=d, author=user)
                ],
            }
        )

    result: dict = {
        "export_generated_at": timezone.now().isoformat(),
        "profile": profile,
        "addresses": addresses,
        "orders": orders,
        "wishlist": wishlist,
        "reviews": reviews,
        "notifications": notifications,
        "notification_preferences": notification_preferences,
        "disputes": disputes,
    }

    if hasattr(user, "supplier"):
        s = user.supplier
        supplier_data: dict = {
            "business_name": s.business_name,
            "status": s.status,
            "description": s.description,
            "website": s.website,
            "phone": s.phone,
            "created_at": s.created_at.isoformat(),
        }
        try:
            addr = s.address
            supplier_data["address"] = {
                "line1": addr.line1,
                "line2": addr.line2,
                "city": addr.city,
                "county": addr.county,
                "postcode": addr.postcode,
                "country": addr.country,
            }
        except Exception:  # noqa: S110  # nosec B110
            pass
        supplier_data["documents"] = [
            {
                "id": str(doc.id),
                "type": doc.document_type,
                "status": doc.status,
                "uploaded_at": doc.uploaded_at.isoformat(),
            }
            for doc in s.documents.all()
        ]
        result["supplier"] = supplier_data

    return result
