import logging
from decimal import Decimal

from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)

_BRAND = "#2D4A3E"
_ACCENT = "#5C8A6E"
_LIGHT = "#F5F2EE"
_TEXT = "#1C2B27"
_MUTED = "#6B7B76"


def _base(title: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:{_LIGHT};font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_LIGHT};padding:40px 0;">
    <tr><td align="center">
      <table width="580" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;border:1px solid #E0DBD4;">
        <!-- Header -->
        <tr>
          <td style="background:{_BRAND};padding:28px 36px;">
            <span style="font-family:Georgia,serif;font-style:italic;font-size:22px;color:#ffffff;letter-spacing:-0.3px;">Provena</span>
          </td>
        </tr>
        <!-- Body -->
        <tr><td style="padding:36px;">
          {body_html}
        </td></tr>
        <!-- Footer -->
        <tr>
          <td style="background:{_LIGHT};padding:20px 36px;border-top:1px solid #E0DBD4;">
            <p style="margin:0;font-size:11px;color:{_MUTED};line-height:1.6;">
              Provena · Fresh produce marketplace<br>
              You received this email because you have an account on Provena.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _h1(text: str) -> str:
    return f'<h1 style="margin:0 0 8px;font-family:Georgia,serif;font-style:italic;font-size:26px;color:{_BRAND};font-weight:normal;">{text}</h1>'


def _p(text: str, muted: bool = False) -> str:
    colour = _MUTED if muted else _TEXT
    return f'<p style="margin:0 0 16px;font-size:14px;color:{colour};line-height:1.6;">{text}</p>'


def _divider() -> str:
    return '<hr style="border:none;border-top:1px solid #E0DBD4;margin:24px 0;">'


def _label(text: str) -> str:
    return f'<p style="margin:0 0 4px;font-size:10px;text-transform:uppercase;letter-spacing:0.12em;color:{_MUTED};font-weight:600;">{text}</p>'


def _value(text: str) -> str:
    return f'<p style="margin:0 0 16px;font-size:14px;color:{_TEXT};font-weight:600;">{text}</p>'


def _items_table(items: list[dict]) -> str:
    rows = ""
    for item in items:
        rows += f"""<tr>
          <td style="padding:10px 0;font-size:13px;color:{_TEXT};border-bottom:1px solid #F0EDE8;">{item["name"]}<br>
            <span style="font-size:11px;color:{_MUTED};">{item["variant"]} · qty {item["quantity"]}</span>
          </td>
          <td style="padding:10px 0;font-size:13px;color:{_TEXT};text-align:right;font-family:monospace;border-bottom:1px solid #F0EDE8;">£{item["subtotal"]}</td>
        </tr>"""
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" style="margin:16px 0;">{rows}</table>'
    )


def _button(text: str, url: str) -> str:
    return f"""<table cellpadding="0" cellspacing="0" style="margin:24px 0;">
      <tr><td style="background:{_BRAND};border-radius:4px;">
        <a href="{url}" style="display:inline-block;padding:12px 24px;font-size:13px;color:#ffffff;text-decoration:none;font-weight:600;">{text}</a>
      </td></tr>
    </table>"""


def _prefs_allow(user, field: str) -> bool:
    from .models import NotificationPreference

    prefs, _ = NotificationPreference.objects.get_or_create(user=user)
    return bool(getattr(prefs, field, True))


def _shipping_display(amount: Decimal) -> str:
    return "Free" if amount == Decimal("0.00") else f"£{amount}"


def send_order_confirmation_buyer(order) -> None:
    """Send order confirmation to the buyer after successful payment."""
    if not _prefs_allow(order.buyer, "email_order_placed"):
        logger.debug("Skipping order confirmation email: user %s opted out", order.buyer.email)
        return
    from django.conf import settings

    frontend = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    order_url = f"{frontend}/orders/{order.reference}"

    items_by_supplier: dict[str, list] = {}
    for sub in order.sub_orders.select_related("supplier").prefetch_related(
        "items__variant__product"
    ):
        items_by_supplier[sub.supplier.business_name] = [
            {
                "name": item.variant.product.name,
                "variant": item.variant.name,
                "quantity": item.quantity,
                "subtotal": str(
                    (Decimal(str(item.unit_price)) * item.quantity).quantize(Decimal("0.01"))
                ),
            }
            for item in sub.items.all()
        ]

    supplier_blocks = ""
    for supplier_name, items in items_by_supplier.items():
        supplier_blocks += f'<p style="margin:16px 0 4px;font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:{_MUTED};font-weight:600;">{supplier_name}</p>'
        supplier_blocks += _items_table(items)

    address = (
        f"{order.shipping_name}, {order.shipping_line1}"
        f"{', ' + order.shipping_line2 if order.shipping_line2 else ''}"
        f", {order.shipping_city}, {order.shipping_postcode}"
    )

    body = (
        _h1("Order confirmed")
        + _p("Thank you for your order. We've received your payment and notified your suppliers.")
        + _divider()
        + _label("Order reference")
        + _value(order.reference)
        + _label("Goods")
        + _value(f"£{order.goods_subtotal}")
        + _label("Shipping")
        + _value(_shipping_display(order.shipping_amount))
        + _label("Includes VAT")
        + _value(f"£{order.vat_amount}")
        + _label("Total paid")
        + _value(f"£{order.total_amount}")
        + _label("Delivering to")
        + _value(address)
        + _divider()
        + supplier_blocks
        + _divider()
        + _button("View order", order_url)
        + _p("Your suppliers will confirm and dispatch your items shortly.", muted=True)
    )

    html = _base(f"Order confirmed · {order.reference}", body)
    plain = (
        f"Order confirmed: {order.reference}\n\n"
        f"Goods: £{order.goods_subtotal}\n"
        f"Shipping: {_shipping_display(order.shipping_amount)}\n"
        f"Includes VAT: £{order.vat_amount}\n"
        f"Total: £{order.total_amount}\n"
        f"Delivering to: {address}\n\n"
        f"View your order: {order_url}"
    )

    _send(
        subject=f"Order confirmed · {order.reference}",
        plain=plain,
        html=html,
        to=[order.buyer.email],
    )


def send_order_notification_supplier(sub_order) -> None:
    """Notify a supplier they have a new order to fulfil."""
    if not _prefs_allow(sub_order.supplier.user, "email_new_order"):
        logger.debug(
            "Skipping new order email: supplier %s opted out", sub_order.supplier.user.email
        )
        return
    from django.conf import settings

    frontend = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    orders_url = f"{frontend}/supplier/orders"

    items = [
        {
            "name": item.variant.product.name,
            "variant": item.variant.name,
            "quantity": item.quantity,
            "subtotal": str(
                (Decimal(str(item.unit_price)) * item.quantity).quantize(Decimal("0.01"))
            ),
        }
        for item in sub_order.items.select_related("variant__product").all()
    ]

    order = sub_order.order
    address = (
        f"{order.shipping_name}, {order.shipping_line1}"
        f"{', ' + order.shipping_line2 if order.shipping_line2 else ''}"
        f", {order.shipping_city}, {order.shipping_postcode}"
    )

    vat_block = _label("of which VAT") + _value(f"£{sub_order.vat_amount}")
    if sub_order.supplier.vat_number:
        vat_block += _label("Your VAT number") + _value(sub_order.supplier.vat_number)

    body = (
        _h1("New order received")
        + _p("You have a new order to fulfil. Please confirm it as soon as possible.")
        + _divider()
        + _label("Order reference")
        + _value(order.reference)
        + _label("Goods")
        + _value(f"£{sub_order.goods_subtotal}")
        + _label("Shipping")
        + _value(_shipping_display(sub_order.shipping_amount))
        + _label("Subtotal")
        + _value(f"£{sub_order.subtotal}")
        + vat_block
        + _label("Ship to")
        + _value(address)
        + _divider()
        + _items_table(items)
        + _divider()
        + _button("View order", orders_url)
        + _p("Log in to your supplier portal to confirm and dispatch this order.", muted=True)
    )

    html = _base(f"New order · {order.reference}", body)
    plain = (
        f"New order: {order.reference}\n\n"
        f"Goods: £{sub_order.goods_subtotal}\n"
        f"Shipping: {_shipping_display(sub_order.shipping_amount)}\n"
        f"Subtotal: £{sub_order.subtotal}\n"
        f"of which VAT: £{sub_order.vat_amount}\n"
        f"Ship to: {address}\n\n"
        f"View orders: {orders_url}"
    )

    _send(
        subject=f"New order · {order.reference}",
        plain=plain,
        html=html,
        to=[sub_order.supplier.user.email],
    )


def send_welcome(user) -> None:
    """Send a welcome email to a newly registered user."""
    from django.conf import settings

    frontend = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    name = user.first_name or user.email.split("@")[0]

    body = (
        _h1("Welcome to Provena")
        + _p(
            f"Hi {name}, thanks for joining. You can start browsing and ordering fresh produce from our network of local suppliers straight away."
        )
        + _divider()
        + _button("Browse the marketplace", frontend + "/catalogue")
        + _p("If you have any questions, just reply to this email.", muted=True)
    )

    html = _base("Welcome to Provena", body)
    plain = f"Hi {name}, welcome to Provena!\n\nBrowse the marketplace: {frontend}/catalogue"

    _send(subject="Welcome to Provena", plain=plain, html=html, to=[user.email])


def send_password_reset(user, reset_url: str) -> None:
    """Send a password reset link."""
    name = user.first_name or "there"

    body = (
        _h1("Reset your password")
        + _p(f"Hi {name}, we received a request to reset the password for your account.")
        + _divider()
        + _button("Reset password", reset_url)
        + _p(
            "This link expires in 1 hour. If you didn't request a reset, you can ignore this email — your password won't change.",
            muted=True,
        )
    )

    html = _base("Reset your password", body)
    plain = (
        f"Hi {name},\n\nReset your Provena password: {reset_url}\n\nThis link expires in 1 hour."
    )

    _send(subject="Reset your Provena password", plain=plain, html=html, to=[user.email])


def send_shipping_update(sub_order) -> None:
    """Notify the buyer that a sub-order has been dispatched."""
    if not _prefs_allow(sub_order.order.buyer, "email_order_dispatched"):
        logger.debug("Skipping dispatch email: user %s opted out", sub_order.order.buyer.email)
        return
    from django.conf import settings

    frontend = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    order = sub_order.order
    order_url = f"{frontend}/orders/{order.reference}"
    supplier_name = sub_order.supplier.business_name

    tracking_block = ""
    if sub_order.tracking_number:
        tracking_block = (
            _divider() + _label("Tracking reference") + _value(sub_order.tracking_number)
        )

    body = (
        _h1("Your order is on its way")
        + _p(f"Good news - {supplier_name} has dispatched your items.")
        + _divider()
        + _label("Order reference")
        + _value(order.reference)
        + _label("Supplier")
        + _value(supplier_name)
        + tracking_block
        + _divider()
        + _button("Track your order", order_url)
        + _p("Deliveries typically arrive within 1-3 working days.", muted=True)
    )

    html = _base(f"Your order is on its way · {order.reference}", body)
    plain = (
        f"Your order {order.reference} has been dispatched by {supplier_name}.\n"
        + (f"Tracking: {sub_order.tracking_number}\n" if sub_order.tracking_number else "")
        + f"\nView order: {order_url}"
    )

    _send(
        subject=f"Your order is on its way · {order.reference}",
        plain=plain,
        html=html,
        to=[order.buyer.email],
    )


def send_delivery_confirmation(sub_order) -> None:
    """Notify the buyer that a sub-order has been delivered."""
    if not _prefs_allow(sub_order.order.buyer, "email_order_dispatched"):
        logger.debug("Skipping delivery email: user %s opted out", sub_order.order.buyer.email)
        return
    from django.conf import settings

    frontend = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    order = sub_order.order
    order_url = f"{frontend}/orders/{order.reference}"
    supplier_name = sub_order.supplier.business_name

    body = (
        _h1("Your order has been delivered")
        + _p(f"Your items from {supplier_name} have been marked as delivered.")
        + _divider()
        + _label("Order reference")
        + _value(order.reference)
        + _label("Supplier")
        + _value(supplier_name)
        + _divider()
        + _button("View order", order_url)
        + _p(
            "If there is a problem with your order you can raise a dispute or request a return "
            "from the order detail page.",
            muted=True,
        )
    )

    html = _base(f"Order delivered · {order.reference}", body)
    plain = (
        f"Your order {order.reference} from {supplier_name} has been delivered.\n"
        f"\nView order: {order_url}"
    )

    _send(
        subject=f"Order delivered · {order.reference}",
        plain=plain,
        html=html,
        to=[order.buyer.email],
    )


def send_payout_received(payout) -> None:
    """Notify a supplier their payout has been processed."""
    if not _prefs_allow(payout.supplier.user, "email_payout_received"):
        logger.debug("Skipping payout email: supplier %s opted out", payout.supplier.user.email)
        return
    from django.conf import settings

    frontend = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    payouts_url = f"{frontend}/supplier/payouts"
    order_ref = payout.sub_order.order.reference

    body = (
        _h1("Payout processed")
        + _p(f"Your payout for order {order_ref} has been sent to your bank account.")
        + _divider()
        + _label("Gross amount")
        + _value(f"£{payout.gross_amount}")
        + _label("Platform fee")
        + _value(f"£{payout.platform_fee}")
        + _label("Net payout")
        + _value(f"£{payout.net_amount}")
        + _divider()
        + _button("View payouts", payouts_url)
        + _p("Funds typically clear within 2-5 business days depending on your bank.", muted=True)
    )

    html = _base(f"Payout processed · {order_ref}", body)
    plain = (
        f"Payout processed for order {order_ref}\n\n"
        f"Gross: £{payout.gross_amount}\n"
        f"Fee: £{payout.platform_fee}\n"
        f"Net: £{payout.net_amount}\n\n"
        f"View payouts: {payouts_url}"
    )

    _send(
        subject=f"Payout processed · {order_ref}",
        plain=plain,
        html=html,
        to=[payout.supplier.user.email],
    )


def send_data_export_ready_email(user, token: str) -> None:
    from django.conf import settings

    download_url = (
        f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}"
        f"/account/data-export?token={token}"
    )
    body = (
        _p("Your personal data export is ready.")
        + _p("The download link below expires in 24 hours. For security, do not share this link.")
        + _button("Download your data", download_url)
        + _p(
            "If you did not request this export, please contact support immediately.",
            muted=True,
        )
    )
    html = _base("Your data export is ready", body)
    plain = (
        f"Your personal data export is ready.\n\n"
        f"Download your data (expires in 24 hours):\n{download_url}\n\n"
        f"If you did not request this export, please contact support immediately."
    )
    _send(
        subject="Your Provena data export is ready",
        plain=plain,
        html=html,
        to=[user.email],
    )


def _send(subject: str, plain: str, html: str, to: list[str]) -> None:
    from django.conf import settings

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "onboarding@resend.dev")
    try:
        msg = EmailMultiAlternatives(subject=subject, body=plain, from_email=from_email, to=to)
        msg.attach_alternative(html, "text/html")
        msg.send()
        logger.info("Email sent: %s → %s", subject, to)
    except Exception:
        logger.exception("Failed to send email: %s → %s", subject, to)
