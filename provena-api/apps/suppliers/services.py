import logging

import stripe
from django.conf import settings
from django.utils import timezone

from apps.accounts.models import Role, User

from .models import (
    DocumentStatus,
    Supplier,
    SupplierAddress,
    SupplierDocument,
    SupplierStatus,
    _unique_slug,
)

logger = logging.getLogger(__name__)


def create_supplier_profile(
    user: User,
    business_name: str,
    description: str = "",
    phone: str = "",
    website: str = "",
    logo_url: str = "",
    address_data: dict | None = None,
) -> Supplier:
    if hasattr(user, "supplier"):
        raise ValueError("A supplier profile already exists for this user.")

    supplier = Supplier.objects.create(
        user=user,
        business_name=business_name,
        slug=_unique_slug(business_name),
        description=description,
        phone=phone,
        website=website,
        logo_url=logo_url,
    )

    if address_data:
        SupplierAddress.objects.create(supplier=supplier, **address_data)

    if user.role != Role.SUPPLIER:
        user.role = Role.SUPPLIER
        user.save(update_fields=["role"])

    return supplier


def update_supplier_profile(supplier: Supplier, **kwargs: object) -> Supplier:
    address_data = kwargs.pop("address_data", None)

    allowed = {"business_name", "description", "phone", "website", "logo_url"}
    for field, value in kwargs.items():
        if field in allowed:
            setattr(supplier, field, value)
    supplier.save()

    if address_data is not None:
        SupplierAddress.objects.update_or_create(supplier=supplier, defaults=address_data)  # type: ignore[arg-type]

    return supplier


def upload_document(supplier: Supplier, document_type: str, file_url: str) -> SupplierDocument:
    return SupplierDocument.objects.create(
        supplier=supplier,
        document_type=document_type,
        file_url=file_url,
    )


def review_document(
    document: SupplierDocument,
    admin_user: User,
    approved: bool,
    notes: str = "",
) -> SupplierDocument:
    document.status = DocumentStatus.APPROVED if approved else DocumentStatus.REJECTED
    document.notes = notes
    document.reviewed_at = timezone.now()
    document.reviewed_by = admin_user
    document.save()
    return document


def approve_supplier(supplier: Supplier, admin_user: User) -> Supplier:
    supplier.status = SupplierStatus.APPROVED
    supplier.save(update_fields=["status", "updated_at"])
    logger.info("Supplier %s approved by %s", supplier.business_name, admin_user.email)
    return supplier


def suspend_supplier(supplier: Supplier, admin_user: User) -> Supplier:
    supplier.status = SupplierStatus.SUSPENDED
    supplier.save(update_fields=["status", "updated_at"])
    logger.info("Supplier %s suspended by %s", supplier.business_name, admin_user.email)
    return supplier


def reject_supplier(supplier: Supplier, admin_user: User) -> Supplier:
    supplier.status = SupplierStatus.REJECTED
    supplier.save(update_fields=["status", "updated_at"])
    logger.info("Supplier %s rejected by %s", supplier.business_name, admin_user.email)
    return supplier


def set_commission_rate(supplier: Supplier, rate: object) -> Supplier:
    supplier.commission_rate = rate  # type: ignore[assignment]
    supplier.save(update_fields=["commission_rate", "updated_at"])
    return supplier


def create_stripe_connect_account(supplier: Supplier) -> str:
    """Create a Stripe Express account for the supplier and store the account ID."""
    if supplier.stripe_account_id:
        return supplier.stripe_account_id

    if not settings.STRIPE_SECRET_KEY:
        logger.warning("Stripe not configured — skipping Connect account creation")
        return ""

    stripe.api_key = settings.STRIPE_SECRET_KEY
    account = stripe.Account.create(
        type="express",
        country="GB",
        email=supplier.user.email,
        capabilities={"transfers": {"requested": True}},
    )
    supplier.stripe_account_id = account["id"]
    supplier.save(update_fields=["stripe_account_id", "updated_at"])
    return str(account["id"])


def get_stripe_connect_onboarding_url(supplier: Supplier, return_url: str, refresh_url: str) -> str:
    """Return the Stripe-hosted onboarding URL for the supplier to complete KYC."""
    if not supplier.stripe_account_id:
        create_stripe_connect_account(supplier)

    if not supplier.stripe_account_id:
        return ""

    stripe.api_key = settings.STRIPE_SECRET_KEY
    link = stripe.AccountLink.create(
        account=supplier.stripe_account_id,
        refresh_url=refresh_url,
        return_url=return_url,
        type="account_onboarding",
    )
    return str(link["url"])


def handle_connect_account_updated(stripe_account_id: str) -> None:
    """Mark onboarding complete when Stripe confirms the account can accept transfers."""
    try:
        supplier = Supplier.objects.get(stripe_account_id=stripe_account_id)
    except Supplier.DoesNotExist:
        logger.warning("account.updated for unknown Stripe account %s", stripe_account_id)
        return

    stripe.api_key = settings.STRIPE_SECRET_KEY
    account = stripe.Account.retrieve(stripe_account_id)
    is_complete = bool(
        getattr(account, "charges_enabled", False) and getattr(account, "payouts_enabled", False)
    )

    if is_complete and not supplier.stripe_onboarding_complete:
        supplier.stripe_onboarding_complete = True
        supplier.save(update_fields=["stripe_onboarding_complete", "updated_at"])
        logger.info("Stripe Connect onboarding complete for supplier %s", supplier.business_name)
    elif not is_complete and supplier.stripe_onboarding_complete:
        supplier.stripe_onboarding_complete = False
        supplier.save(update_fields=["stripe_onboarding_complete", "updated_at"])
        logger.warning(
            "Stripe Connect account %s lost charges/payouts capability", stripe_account_id
        )


def get_performance_stats(supplier: Supplier) -> dict:
    from decimal import ROUND_HALF_UP, Decimal

    from django.db.models import Sum

    from apps.catalogue.models import Product, ProductStatus
    from apps.orders.models import SubOrder

    _two_dp = Decimal("0.01")

    sub_orders = SubOrder.objects.filter(supplier=supplier)
    total_orders = sub_orders.count()
    total_revenue = sub_orders.aggregate(s=Sum("subtotal"))["s"] or Decimal("0")

    active_products = Product.objects.filter(supplier=supplier, status=ProductStatus.ACTIVE).count()

    return {
        "total_orders": total_orders,
        "total_revenue": str(total_revenue.quantize(_two_dp, rounding=ROUND_HALF_UP)),
        "average_fulfilment_days": None,
        "return_rate": "0.00",
        "active_products": active_products,
    }
