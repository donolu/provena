import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class SupplierStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Review"
    APPROVED = "APPROVED", "Approved"
    SUSPENDED = "SUSPENDED", "Suspended"
    REJECTED = "REJECTED", "Rejected"


class ShippingPolicy(models.TextChoices):
    FLAT = "FLAT", "Flat rate"
    FREE_OVER_THRESHOLD = "FREE_OVER_THRESHOLD", "Free over threshold"
    PER_ITEM = "PER_ITEM", "Per item"


class FulfilmentMode(models.TextChoices):
    SUPPLIER_SHIP = "SUPPLIER_SHIP", "Supplier ships"
    PLATFORM_DELIVERY = "PLATFORM_DELIVERY", "Platform-brokered delivery"


class DocumentType(models.TextChoices):
    IDENTITY = "IDENTITY", "Identity Document"
    BUSINESS_REG = "BUSINESS_REG", "Business Registration"
    FOOD_HYGIENE = "FOOD_HYGIENE", "Food Hygiene Certificate"
    ORGANIC_CERT = "ORGANIC_CERT", "Organic Certification"
    OTHER = "OTHER", "Other"


class DocumentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


def _unique_slug(business_name: str) -> str:
    base = slugify(business_name)
    slug = base
    n = 1
    while Supplier.objects.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


class Supplier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="supplier"
    )
    business_name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    logo_url = models.URLField(blank=True)
    website = models.URLField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    status = models.CharField(
        max_length=10, choices=SupplierStatus.choices, default=SupplierStatus.PENDING
    )
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("10.00"))
    vat_registered = models.BooleanField(default=False)
    vat_number = models.CharField(max_length=20, blank=True)
    shipping_policy = models.CharField(
        max_length=20, choices=ShippingPolicy.choices, default=ShippingPolicy.FLAT
    )
    shipping_flat_rate = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00")
    )
    shipping_per_item_rate = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00")
    )
    free_shipping_threshold = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    # Platform-brokered delivery (ADR-013): a commercial arrangement the platform configures.
    # When PLATFORM_DELIVERY, the flat platform_delivery_fee replaces the supplier's own policy
    # and the fee is kept by the platform (not added to the supplier's payout gross).
    fulfilment_mode = models.CharField(
        max_length=20, choices=FulfilmentMode.choices, default=FulfilmentMode.SUPPLIER_SHIP
    )
    platform_delivery_fee = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00")
    )
    stripe_account_id = models.CharField(max_length=100, blank=True)
    stripe_onboarding_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.business_name

    @property
    def is_approved(self) -> bool:
        return self.status == SupplierStatus.APPROVED

    def compute_shipping(self, goods_subtotal: Decimal, total_quantity: int) -> Decimal:
        """Shipping charged for a sub-order under this supplier's policy.

        FREE_OVER_THRESHOLD is evaluated on the pre-discount goods value (ADR-012 §4).
        The pricing pass quantises the result at the stored boundary.
        """
        # Platform-brokered delivery: a flat platform-set fee (a real courier cost), so no
        # free-over-threshold and the supplier's own policy does not apply (ADR-013).
        if self.fulfilment_mode == FulfilmentMode.PLATFORM_DELIVERY:
            return self.platform_delivery_fee
        if self.shipping_policy == ShippingPolicy.PER_ITEM:
            return self.shipping_per_item_rate * total_quantity
        if (
            self.shipping_policy == ShippingPolicy.FREE_OVER_THRESHOLD
            and self.free_shipping_threshold is not None
            and goods_subtotal >= self.free_shipping_threshold
        ):
            return Decimal("0.00")
        return self.shipping_flat_rate


class SupplierAddress(models.Model):
    supplier = models.OneToOneField(Supplier, on_delete=models.CASCADE, related_name="address")
    line1 = models.CharField(max_length=200)
    line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100)
    county = models.CharField(max_length=100, blank=True)
    postcode = models.CharField(max_length=10)
    country = models.CharField(max_length=2, default="GB")

    def __str__(self) -> str:
        return f"{self.line1}, {self.city}, {self.postcode}"


class SupplierDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    file_url = models.URLField()
    status = models.CharField(
        max_length=10, choices=DocumentStatus.choices, default=DocumentStatus.PENDING
    )
    notes = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_documents",
    )

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return f"{self.get_document_type_display()} — {self.supplier.business_name}"
