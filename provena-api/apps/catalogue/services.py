import logging

from apps.accounts.models import User

from .models import (
    Category,
    Product,
    ProductImage,
    ProductStatus,
    ProductVariant,
    VariantImage,
    _unique_category_slug,
    _unique_product_slug,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------


def create_category(
    name: str,
    parent: Category | None = None,
    description: str = "",
    image_url: str = "",
    position: int = 0,
) -> Category:
    return Category.objects.create(
        name=name,
        slug=_unique_category_slug(name),
        parent=parent,
        description=description,
        image_url=image_url,
        position=position,
    )


def update_category(category: Category, **kwargs: object) -> Category:
    allowed = {"name", "description", "image_url", "parent", "position", "is_active"}
    for field, value in kwargs.items():
        if field in allowed:
            setattr(category, field, value)
    category.save()
    return category


def delete_category(category: Category) -> None:
    category.delete()


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------


def create_product(
    supplier: object,
    name: str,
    description: str = "",
    category: Category | None = None,
) -> Product:
    return Product.objects.create(
        supplier=supplier,  # type: ignore[misc]
        name=name,
        slug=_unique_product_slug(name),
        description=description,
        category=category,
        status=ProductStatus.DRAFT,
    )


def update_product(product: Product, **kwargs: object) -> Product:
    allowed = {"name", "description", "category"}
    for field, value in kwargs.items():
        if field in allowed:
            setattr(product, field, value)
    product.save()
    return product


def publish_product(product: Product) -> Product:
    if product.status == ProductStatus.ARCHIVED:
        raise ValueError("Archived products cannot be published. Create a new product instead.")
    product.status = ProductStatus.ACTIVE
    product.save(update_fields=["status", "updated_at"])
    logger.info("Product %s published", product.slug)
    return product


def archive_product(product: Product) -> Product:
    product.status = ProductStatus.ARCHIVED
    product.save(update_fields=["status", "updated_at"])
    logger.info("Product %s archived", product.slug)
    return product


def feature_product(product: Product, admin_user: User) -> Product:
    product.is_featured = True
    product.save(update_fields=["is_featured", "updated_at"])
    logger.info("Product %s featured by %s", product.slug, admin_user.email)
    return product


def bulk_update_products(
    slugs: list[str],
    action: str,
    status: str | None = None,
    category: "Category | None" = None,
    is_featured: bool | None = None,
) -> int:
    qs = Product.objects.filter(slug__in=slugs)
    if action == "set_status":
        updated = qs.update(status=status)
    elif action == "set_category":
        updated = qs.update(category=category)
    else:
        updated = qs.update(is_featured=bool(is_featured))
    logger.info("Bulk %s applied to %d products", action, updated)
    return updated


def unfeature_product(product: Product, admin_user: User) -> Product:
    product.is_featured = False
    product.save(update_fields=["is_featured", "updated_at"])
    logger.info("Product %s unfeatured by %s", product.slug, admin_user.email)
    return product


# ---------------------------------------------------------------------------
# Variants
# ---------------------------------------------------------------------------


def add_variant(
    product: Product,
    name: str,
    sku: str,
    price: object,
    compare_at_price: object = None,
    weight_grams: int = 0,
) -> ProductVariant:
    if ProductVariant.objects.filter(sku=sku).exists():
        raise ValueError(f"SKU '{sku}' is already in use.")
    return ProductVariant.objects.create(
        product=product,
        name=name,
        sku=sku,
        price=price,  # type: ignore[misc]
        compare_at_price=compare_at_price,
        weight_grams=weight_grams,
    )


def update_variant(variant: ProductVariant, **kwargs: object) -> ProductVariant:
    allowed = {"name", "sku", "price", "compare_at_price", "weight_grams", "is_active"}
    if "sku" in kwargs and kwargs["sku"] != variant.sku:
        if ProductVariant.objects.filter(sku=kwargs["sku"]).exists():
            raise ValueError(f"SKU '{kwargs['sku']}' is already in use.")
    for field, value in kwargs.items():
        if field in allowed:
            setattr(variant, field, value)
    variant.save()
    return variant


def remove_variant(variant: ProductVariant) -> None:
    variant.delete()


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------


def add_image(
    product: Product,
    url: str,
    alt_text: str = "",
    position: int | None = None,
    is_primary: bool = False,
) -> ProductImage:
    if position is None:
        last = product.images.order_by("-position").first()
        position = (last.position + 1) if last else 0

    if is_primary:
        product.images.filter(is_primary=True).update(is_primary=False)

    return ProductImage.objects.create(
        product=product,
        url=url,
        alt_text=alt_text,
        position=position,
        is_primary=is_primary,
    )


def update_image(image: ProductImage, **kwargs: object) -> ProductImage:
    allowed = {"url", "alt_text", "position", "is_primary"}
    if kwargs.get("is_primary"):
        image.product.images.filter(is_primary=True).exclude(pk=image.pk).update(is_primary=False)
    for field, value in kwargs.items():
        if field in allowed:
            setattr(image, field, value)
    image.save()
    return image


def remove_image(image: ProductImage) -> None:
    image.delete()


# ---------------------------------------------------------------------------
# Variant images
# ---------------------------------------------------------------------------


def add_variant_image(
    variant: ProductVariant,
    url: str,
    alt_text: str = "",
    position: int | None = None,
    is_primary: bool = False,
) -> VariantImage:
    if position is None:
        last = variant.images.order_by("-position").first()
        position = (last.position + 1) if last else 0

    if is_primary:
        variant.images.filter(is_primary=True).update(is_primary=False)

    return VariantImage.objects.create(
        variant=variant,
        url=url,
        alt_text=alt_text,
        position=position,
        is_primary=is_primary,
    )


def update_variant_image(image: VariantImage, **kwargs: object) -> VariantImage:
    allowed = {"url", "alt_text", "position", "is_primary"}
    if kwargs.get("is_primary"):
        image.variant.images.filter(is_primary=True).exclude(pk=image.pk).update(is_primary=False)
    for field, value in kwargs.items():
        if field in allowed:
            setattr(image, field, value)
    image.save()
    return image


def remove_variant_image(image: VariantImage) -> None:
    image.delete()
