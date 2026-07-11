"""Typesense full-text product search.

Thin wrapper around the Typesense client. Everything here is a no-op when
``settings.TYPESENSE_ENABLED`` is false (no ``TYPESENSE_HOST`` configured), so
development and CI run without a Typesense instance and product search falls
back to the Postgres ILIKE query in the view.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from django.conf import settings

if TYPE_CHECKING:
    import typesense

    from .models import Product

logger = logging.getLogger(__name__)

# One schema field per thing we want to search or filter on. Prices are the
# cheapest/priciest active variant so a min/max price filter can match the same
# products the Postgres query does (a product with *any* variant in range).
PRODUCTS_SCHEMA: dict[str, Any] = {
    "name": settings.TYPESENSE_PRODUCTS_COLLECTION,
    "enable_nested_fields": False,
    "fields": [
        {"name": "name", "type": "string"},
        {"name": "description", "type": "string"},
        {"name": "category", "type": "string", "facet": True, "optional": True},
        {"name": "category_slug", "type": "string", "facet": True, "optional": True},
        {"name": "supplier", "type": "string", "facet": True},
        {"name": "supplier_slug", "type": "string", "facet": True},
        {"name": "variant_names", "type": "string[]"},
        {"name": "skus", "type": "string[]"},
        {"name": "min_price", "type": "float"},
        {"name": "max_price", "type": "float"},
        {"name": "is_featured", "type": "bool", "facet": True},
        {"name": "created_at", "type": "int64"},
    ],
    "default_sorting_field": "created_at",
}

QUERY_BY = "name,description,category,supplier,variant_names,skus"
# Relevance first, then featured, then newest — mirrors the browse ordering.
SORT_BY = "_text_match:desc,is_featured:desc,created_at:desc"


@lru_cache(maxsize=1)
def get_client() -> typesense.Client | None:
    """Return a cached Typesense client, or None when search is disabled."""
    if not settings.TYPESENSE_ENABLED:
        return None
    import typesense

    return typesense.Client(
        {
            "nodes": [
                {
                    "host": settings.TYPESENSE_HOST,
                    "port": settings.TYPESENSE_PORT,
                    "protocol": settings.TYPESENSE_PROTOCOL,
                }
            ],
            "api_key": settings.TYPESENSE_API_KEY,
            "connection_timeout_seconds": settings.TYPESENSE_TIMEOUT_SECONDS,
        }
    )


def ensure_collection() -> None:
    """Create the products collection if it does not already exist."""
    client = get_client()
    if client is None:
        return
    try:
        client.collections[settings.TYPESENSE_PRODUCTS_COLLECTION].retrieve()
    except Exception:
        client.collections.create(PRODUCTS_SCHEMA)  # type: ignore[arg-type]


def _price_bounds(product: Product) -> tuple[float, float]:
    prices = [v.price for v in product.variants.all() if v.is_active]
    if not prices:
        return 0.0, 0.0
    return float(min(prices)), float(max(prices))


def build_document(product: Product) -> dict[str, Any]:
    """Serialise a Product into a Typesense document."""
    variants = list(product.variants.all())
    min_price, max_price = _price_bounds(product)
    created = product.created_at
    return {
        "id": str(product.id),
        "name": product.name,
        "description": product.description or "",
        "category": product.category.name if product.category else "",
        "category_slug": product.category.slug if product.category else "",
        "supplier": product.supplier.business_name,
        "supplier_slug": product.supplier.slug,
        "variant_names": [v.name for v in variants],
        "skus": [v.sku for v in variants],
        "min_price": min_price,
        "max_price": max_price,
        "is_featured": product.is_featured,
        "created_at": int(created.timestamp()) if created else 0,
    }


def index_product(product: Product) -> None:
    """Upsert one product document. Safe to call when search is disabled."""
    client = get_client()
    if client is None:
        return
    ensure_collection()
    client.collections[settings.TYPESENSE_PRODUCTS_COLLECTION].documents.upsert(
        build_document(product)
    )


def delete_product(product_id: str) -> None:
    """Remove one product document by id.

    A missing document is fine (never indexed, or an unpublished product), but
    transport/auth/server errors propagate so the calling Celery task retries
    instead of silently leaving a stale document in the index.
    """
    client = get_client()
    if client is None:
        return
    from typesense.exceptions import ObjectNotFound

    try:
        client.collections[settings.TYPESENSE_PRODUCTS_COLLECTION].documents[
            str(product_id)
        ].delete()
    except ObjectNotFound:
        logger.debug("Typesense delete: document %s not found", product_id)


def _build_filter(
    *,
    category_slug: str | None,
    supplier_slug: str | None,
    min_price: str | None,
    max_price: str | None,
    featured: bool,
) -> str:
    clauses = []
    if category_slug:
        clauses.append(f"category_slug:={category_slug}")
    if supplier_slug:
        clauses.append(f"supplier_slug:={supplier_slug}")
    if featured:
        clauses.append("is_featured:=true")
    # A product matches a price floor if its dearest variant clears it, and a
    # price ceiling if its cheapest variant is under it — the same "any variant
    # in range" semantics as the Postgres filter.
    if min_price:
        clauses.append(f"max_price:>={Decimal(min_price)}")
    if max_price:
        clauses.append(f"min_price:<={Decimal(max_price)}")
    return " && ".join(clauses)


def search_products(
    query: str,
    *,
    category_slug: str | None = None,
    supplier_slug: str | None = None,
    min_price: str | None = None,
    max_price: str | None = None,
    featured: bool = False,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[str], int]:
    """Return ``(product_ids, total_found)`` for one page of results.

    Typesense does the paging, so only the ids for the requested page are
    returned. Raises on transport/search errors so the caller can fall back to
    Postgres.
    """
    client = get_client()
    if client is None:
        raise RuntimeError("Typesense is not configured")

    params: dict[str, Any] = {
        "q": query,
        "query_by": QUERY_BY,
        "sort_by": SORT_BY,
        "per_page": max(1, min(per_page, 250)),
        "page": max(1, page),
        "include_fields": "id",
    }
    filter_by = _build_filter(
        category_slug=category_slug,
        supplier_slug=supplier_slug,
        min_price=min_price,
        max_price=max_price,
        featured=featured,
    )
    if filter_by:
        params["filter_by"] = filter_by

    result = client.collections[settings.TYPESENSE_PRODUCTS_COLLECTION].documents.search(
        params  # type: ignore[arg-type]
    )
    ids: list[str] = [str(hit["document"]["id"]) for hit in result.get("hits", [])]
    return ids, int(result.get("found", len(ids)))
