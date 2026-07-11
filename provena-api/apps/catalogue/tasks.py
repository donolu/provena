"""Celery tasks that keep the Typesense product index in sync.

All tasks no-op when search is disabled (see apps.catalogue.search), so they are
safe to enqueue unconditionally.
"""

import logging

from celery import shared_task
from django.conf import settings

from . import search

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def index_product(self, product_id: str) -> None:
    """(Re)index a single product, or drop it from the index when it is no
    longer an active product (draft/archived or deleted)."""
    if not settings.TYPESENSE_ENABLED:
        return

    from .models import Product, ProductStatus

    try:
        product = (
            Product.objects.select_related("category", "supplier")
            .prefetch_related("variants")
            .get(pk=product_id)
        )
    except Product.DoesNotExist:
        search.delete_product(product_id)
        return

    try:
        if product.status == ProductStatus.ACTIVE:
            search.index_product(product)
        else:
            search.delete_product(product_id)
    except Exception as exc:
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def delete_product(self, product_id: str) -> None:
    if not settings.TYPESENSE_ENABLED:
        return
    try:
        search.delete_product(product_id)
    except Exception as exc:
        raise self.retry(exc=exc) from exc


@shared_task
def reindex_all_products() -> int:
    """Rebuild the whole index from the active catalogue. Returns the count."""
    if not settings.TYPESENSE_ENABLED:
        return 0

    from .models import Product, ProductStatus

    search.ensure_collection()
    products = (
        Product.objects.filter(status=ProductStatus.ACTIVE)
        .select_related("category", "supplier")
        .prefetch_related("variants")
    )
    count = 0
    # chunk_size is required to combine iterator() with prefetch_related().
    for product in products.iterator(chunk_size=500):
        search.index_product(product)
        count += 1
    logger.info("Reindexed %d products into Typesense", count)
    return count
