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


class ReturnPolicy(models.TextChoices):
    # The two UK Consumer Contracts Regulations 2013 exemption classes relevant here,
    # plus the default. Defects/spoilage are always redressable via a dispute (CRA 2015).
    #
    # Standard 14-day change-of-mind return.
    RETURNABLE = "RETURNABLE", "Returnable (14-day change of mind)"
    # Perishable/exempt goods: no change-of-mind return at all (reg 28(3)(c)).
    DEFECTIVE_ONLY = "DEFECTIVE_ONLY", "Defective only (via dispute)"
    # Sealed goods unsuitable for return for hygiene/health reasons *once unsealed*
    # (reg 28(3)(b)). The right survives while the item is unopened, and the platform
    # cannot observe the seal, so a return request is allowed (like RETURNABLE) with an
    # "only if unopened" condition; the supplier verifies the seal on inspection.
    SEALED = "SEALED", "Sealed for hygiene (returnable only if unopened)"


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
    # Default return policy for products in this category. Defaults to DEFECTIVE_ONLY:
    # this is a fresh-produce marketplace, so most goods are perishable and exempt from
    # the change-of-mind return right (ADR-014). Admins set non-perishable categories to
    # RETURNABLE; a product may override its category (see Product.effective_return_policy).
    return_policy = models.CharField(
        max_length=16, choices=ReturnPolicy.choices, default=ReturnPolicy.DEFECTIVE_ONLY
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
    # Optional per-product override of the category's return policy; blank = inherit the
    # category default (ADR-014). Resolve via effective_return_policy.
    return_policy_override = models.CharField(
        max_length=16, choices=ReturnPolicy.choices, blank=True, default=""
    )
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

    @property
    def effective_return_policy(self) -> str:
        """The product's return policy: its own override, else the category default,
        else DEFECTIVE_ONLY when the product has no category (safe for perishables)."""
        if self.return_policy_override:
            return self.return_policy_override
        category = self.category
        if category is not None:
            return category.return_policy
        return ReturnPolicy.DEFECTIVE_ONLY


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
