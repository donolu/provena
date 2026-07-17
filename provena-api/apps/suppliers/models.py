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
