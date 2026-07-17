import uuid
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify


class ProductStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    ARCHIVED = "ARCHIVED", "Archived"


class VatRate(models.TextChoices):
    STANDARD = "STANDARD", "Standard (20%)"
    REDUCED = "REDUCED", "Reduced (5%)"
    ZERO = "ZERO", "Zero (0%)"


# Fraction of the net price that VAT adds; prices are VAT-inclusive, so VAT is
# extracted from the gross rather than added on top (see ADR-012).
VAT_RATE_FRACTIONS: dict[str, Decimal] = {
    VatRate.STANDARD: Decimal("0.20"),
    VatRate.REDUCED: Decimal("0.05"),
    VatRate.ZERO: Decimal("0.00"),
}


def _unique_product_slug(name: str) -> str:
    base = slugify(name)
    slug = base
    n = 1
    while Product.objects.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


def _unique_category_slug(name: str) -> str:
    base = slugify(name)
    slug = base
    n = 1
    while Category.objects.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    dispute_window_days = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(7)],
    )

    class Meta:
        ordering = ["position", "name"]
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    supplier = models.ForeignKey(
        "suppliers.Supplier", on_delete=models.CASCADE, related_name="products"
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="products",
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=10, choices=ProductStatus.choices, default=ProductStatus.DRAFT
    )
    vat_rate = models.CharField(max_length=10, choices=VatRate.choices, default=VatRate.STANDARD)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name

    @property
    def is_published(self) -> bool:
        return self.status == ProductStatus.ACTIVE


class ProductVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField(max_length=120)
    sku = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    weight_grams = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["price"]

    def __str__(self) -> str:
        return f"{self.product.name} — {self.name} ({self.sku})"

    @property
    def on_sale(self) -> bool:
        return self.compare_at_price is not None and self.compare_at_price > self.price

    @property
    def discount_percent(self) -> Decimal | None:
        if not self.on_sale or not self.compare_at_price:
            return None
        return ((self.compare_at_price - self.price) / self.compare_at_price * 100).quantize(
            Decimal("0.01")
        )


class ProductImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    url = models.URLField()
    alt_text = models.CharField(max_length=200, blank=True)
    position = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["position"]

    def __str__(self) -> str:
        return f"{self.product.name} image ({self.position})"


class VariantImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="images")
    url = models.URLField()
    alt_text = models.CharField(max_length=200, blank=True)
    position = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["position"]

    def __str__(self) -> str:
        return f"{self.variant} image ({self.position})"


class Banner(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=120)
    subtitle = models.TextField(blank=True)
    image_url = models.URLField()
    link = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position"]

    def __str__(self) -> str:
        return self.title
