"""Keep the search index in step with catalogue changes.

Handlers enqueue Celery tasks after the transaction commits. They short-circuit
when search is disabled, so with no Typesense configured (dev/CI) nothing is
enqueued and the database is never asked to reach Redis on save.
"""

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Product, ProductVariant
from .tasks import delete_product, index_product


def _enqueue_index(product_id) -> None:
    if not settings.TYPESENSE_ENABLED:
        return
    transaction.on_commit(lambda: index_product.delay(str(product_id)))


@receiver(post_save, sender=Product, dispatch_uid="catalogue.index_product_on_save")
def index_product_on_save(sender, instance: Product, **kwargs) -> None:
    _enqueue_index(instance.pk)


@receiver(post_delete, sender=Product, dispatch_uid="catalogue.delete_product_on_delete")
def delete_product_on_delete(sender, instance: Product, **kwargs) -> None:
    if not settings.TYPESENSE_ENABLED:
        return
    product_id = str(instance.pk)
    transaction.on_commit(lambda: delete_product.delay(product_id))


@receiver(
    [post_save, post_delete],
    sender=ProductVariant,
    dispatch_uid="catalogue.reindex_product_on_variant_change",
)
def reindex_product_on_variant_change(sender, instance: ProductVariant, **kwargs) -> None:
    # Variant name/sku/price all feed the product document, so any variant change
    # reindexes the parent product.
    _enqueue_index(instance.product_id)
