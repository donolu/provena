import hashlib
import secrets
from datetime import timedelta

from celery import shared_task
from django.utils import timezone


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

        from apps.notifications.email_service import send_data_export_ready_email

        send_data_export_ready_email(export.user, token)

    except Exception:
        export.status = DataExportStatus.FAILED
        export.save(update_fields=["status"])
        raise


def _collect_user_data(user) -> dict:
    from apps.disputes.models import Dispute
    from apps.notifications.models import Notification
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
        .prefetch_related("sub_orders__items", "sub_orders__supplier")
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

    disputes = [
        {
            "id": str(d.id),
            "sub_order": str(d.sub_order_id),
            "type": d.dispute_type,
            "status": d.status,
            "description": d.description,
            "resolution_requested": d.resolution_requested,
            "outcome": d.outcome,
            "opened_at": d.opened_at.isoformat(),
            "resolved_at": d.resolved_at.isoformat() if d.resolved_at else None,
        }
        for d in Dispute.objects.filter(opened_by=user)
    ]

    return {
        "export_generated_at": timezone.now().isoformat(),
        "profile": profile,
        "addresses": addresses,
        "orders": orders,
        "notifications": notifications,
        "disputes": disputes,
    }
