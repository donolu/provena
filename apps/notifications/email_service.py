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
          <td style="padding:10px 0;font-size:13px;color:{_TEXT};border-bottom:1px solid #F0EDE8;">{item['name']}<br>
            <span style="font-size:11px;color:{_MUTED};">{item['variant']} · qty {item['quantity']}</span>
          </td>
          <td style="padding:10px 0;font-size:13px;color:{_TEXT};text-align:right;font-family:monospace;border-bottom:1px solid #F0EDE8;">£{item['subtotal']}</td>
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


def send_order_confirmation_buyer(order) -> None:
    """Send order confirmation to the buyer after successful payment."""
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

    body = (
        _h1("New order received")
        + _p("You have a new order to fulfil. Please confirm it as soon as possible.")
        + _divider()
        + _label("Order reference")
        + _value(order.reference)
        + _label("Subtotal")
        + _value(f"£{sub_order.subtotal}")
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
        f"Subtotal: £{sub_order.subtotal}\n"
        f"Ship to: {address}\n\n"
        f"View orders: {orders_url}"
    )

    _send(
        subject=f"New order · {order.reference}",
        plain=plain,
        html=html,
        to=[sub_order.supplier.user.email],
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
