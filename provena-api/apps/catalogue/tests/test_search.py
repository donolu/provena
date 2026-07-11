from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.catalogue import search
from apps.catalogue.models import Product, ProductStatus, ProductVariant
from apps.catalogue.tasks import delete_product, index_product, reindex_all_products

LIST_URL = "/api/v1/catalogue/products/"


def _product(supplier, category, name, slug, *, prices=("5.00",), status=ProductStatus.ACTIVE):
    product = Product.objects.create(
        supplier=supplier, category=category, name=name, slug=slug, status=status
    )
    for i, price in enumerate(prices):
        ProductVariant.objects.create(
            product=product, name=f"v{i}", sku=f"{slug}-{i}", price=Decimal(price)
        )
    return product


@pytest.mark.django_db
class TestSearchFallback:
    def test_disabled_uses_postgres_ilike(self, api_client, approved_supplier, category):
        _product(approved_supplier, category, "Bramley Apples", "apples")
        _product(approved_supplier, category, "Carrots", "carrots")

        # TYPESENSE_ENABLED defaults to False in tests.
        res = api_client.get(LIST_URL, {"search": "apple"})
        assert res.status_code == 200
        slugs = [p["slug"] for p in res.json()["results"]]
        assert slugs == ["apples"]

    @override_settings(TYPESENSE_ENABLED=True)
    @patch("apps.catalogue.views.search.search_products")
    def test_typesense_ranks_results(self, mock_search, api_client, approved_supplier, category):
        a = _product(approved_supplier, category, "Apple A", "a")
        b = _product(approved_supplier, category, "Apple B", "b")
        c = _product(approved_supplier, category, "Apple C", "c")
        # Typesense returns c, a (ranked), b excluded.
        mock_search.return_value = ([str(c.id), str(a.id)], 2)

        res = api_client.get(LIST_URL, {"search": "apple"})
        assert res.status_code == 200
        body = res.json()
        assert body["count"] == 2
        assert [p["slug"] for p in body["results"]] == ["c", "a"]  # rank preserved
        assert b.slug not in [p["slug"] for p in body["results"]]

    @override_settings(TYPESENSE_ENABLED=True)
    @patch("apps.catalogue.views.search.search_products", side_effect=ConnectionError("down"))
    def test_typesense_unavailable_matches_fallback(
        self, mock_search, api_client, approved_supplier, category
    ):
        _product(approved_supplier, category, "Bramley Apples", "apples")
        _product(approved_supplier, category, "Carrots", "carrots")

        res = api_client.get(LIST_URL, {"search": "apple"})
        assert res.status_code == 200
        mock_search.assert_called_once()
        # Same result as the pure-Postgres fallback: search engine outage is invisible.
        assert [p["slug"] for p in res.json()["results"]] == ["apples"]

    @override_settings(TYPESENSE_ENABLED=True)
    @patch("apps.catalogue.views.search.search_products")
    def test_empty_search_stays_on_postgres(
        self, mock_search, api_client, approved_supplier, category
    ):
        _product(approved_supplier, category, "Apples", "apples")

        res = api_client.get(LIST_URL, {"category": category.slug})  # no search term
        assert res.status_code == 200
        mock_search.assert_not_called()


@pytest.mark.django_db
class TestSearchIndexing:
    def test_build_document(self, approved_supplier, category):
        product = _product(
            approved_supplier, category, "Heritage Tomatoes", "tomatoes", prices=("3.00", "8.50")
        )
        doc = search.build_document(product)
        assert doc["id"] == str(product.id)
        assert doc["name"] == "Heritage Tomatoes"
        assert doc["category"] == category.name
        assert doc["supplier"] == approved_supplier.business_name
        assert doc["min_price"] == 3.0
        assert doc["max_price"] == 8.5
        assert sorted(doc["skus"]) == ["tomatoes-0", "tomatoes-1"]

    @override_settings(TYPESENSE_ENABLED=True)
    @patch("apps.catalogue.tasks.search")
    def test_index_task_indexes_active_and_removes_inactive(
        self, mock_search, approved_supplier, category
    ):
        active = _product(approved_supplier, category, "Active", "active")
        draft = _product(approved_supplier, category, "Draft", "draft", status=ProductStatus.DRAFT)

        index_product.apply(args=[str(active.id)])
        mock_search.index_product.assert_called_once()
        mock_search.delete_product.assert_not_called()

        mock_search.reset_mock()
        index_product.apply(args=[str(draft.id)])
        mock_search.delete_product.assert_called_once_with(str(draft.id))
        mock_search.index_product.assert_not_called()

    @override_settings(TYPESENSE_ENABLED=False)
    @patch("apps.catalogue.tasks.search")
    def test_index_task_noops_when_disabled(self, mock_search, approved_supplier, category):
        product = _product(approved_supplier, category, "Active", "active")
        index_product.apply(args=[str(product.id)])
        mock_search.index_product.assert_not_called()
        mock_search.delete_product.assert_not_called()

    @override_settings(TYPESENSE_ENABLED=True)
    @patch("apps.catalogue.signals.index_product")
    def test_save_enqueues_index_when_enabled(
        self, mock_task, approved_supplier, category, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            _product(approved_supplier, category, "New", "new")
        mock_task.delay.assert_called()

    @patch("apps.catalogue.signals.index_product")
    def test_save_does_not_enqueue_when_disabled(
        self, mock_task, approved_supplier, category, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            _product(approved_supplier, category, "New", "new")
        mock_task.delay.assert_not_called()

    @override_settings(TYPESENSE_ENABLED=True)
    @patch("apps.catalogue.tasks.search")
    def test_delete_task_removes_document(self, mock_search, approved_supplier, category):
        product = _product(approved_supplier, category, "Gone", "gone")
        delete_product.apply(args=[str(product.id)])
        mock_search.delete_product.assert_called_once_with(str(product.id))

    @override_settings(TYPESENSE_ENABLED=True)
    @patch("apps.catalogue.tasks.search")
    def test_reindex_all_indexes_only_active(self, mock_search, approved_supplier, category):
        _product(approved_supplier, category, "A", "a")
        _product(approved_supplier, category, "B", "b")
        _product(approved_supplier, category, "Draft", "draft", status=ProductStatus.DRAFT)

        count = reindex_all_products()
        assert count == 2
        assert mock_search.index_product.call_count == 2
        mock_search.ensure_collection.assert_called_once()

    def test_reindex_all_noops_when_disabled(self, approved_supplier, category):
        _product(approved_supplier, category, "A", "a")
        assert reindex_all_products() == 0

    def test_shared_task_uses_configured_redis_broker(self):
        # Regression: config/__init__ must load the Celery app so a shared_task's
        # .delay() reaches the configured Redis broker. Without it the web and
        # management processes fall back to Celery's default broker and every
        # enqueue (search indexing, data exports, payouts) raises ConnectionError.
        from django.conf import settings

        broker = index_product.app.conf.broker_url
        assert broker == settings.CELERY_BROKER_URL
        assert broker and "redis" in broker

    @override_settings(TYPESENSE_ENABLED=True)
    @patch("apps.catalogue.tasks.reindex_all_products", return_value=3)
    def test_reindex_command_runs_when_enabled(self, mock_reindex):
        call_command("reindex_search")
        mock_reindex.assert_called_once()

    def test_reindex_command_errors_when_disabled(self):
        with pytest.raises(CommandError):
            call_command("reindex_search")


@pytest.mark.django_db
class TestSearchClient:
    def test_get_client_none_when_disabled(self):
        search.get_client.cache_clear()
        assert search.get_client() is None
        search.get_client.cache_clear()

    def test_ensure_collection_noops_when_disabled(self):
        # No client, so this must simply return without error.
        search.ensure_collection()


@pytest.mark.django_db
class TestSearchModule:
    """Exercise the search module's client operations with a mocked Typesense
    client, so the transport logic is covered without a live engine."""

    def _collection(self, mock_client):
        return mock_client.collections.__getitem__.return_value

    def test_ensure_collection_creates_when_missing(self):
        client = MagicMock()
        self._collection(client).retrieve.side_effect = Exception("404")
        with patch("apps.catalogue.search.get_client", return_value=client):
            search.ensure_collection()
        client.collections.create.assert_called_once()

    def test_ensure_collection_skips_when_present(self):
        client = MagicMock()
        with patch("apps.catalogue.search.get_client", return_value=client):
            search.ensure_collection()
        client.collections.create.assert_not_called()

    def test_index_product_upserts_document(self, approved_supplier, category):
        product = _product(approved_supplier, category, "Kale", "kale", prices=("2.00", "6.00"))
        client = MagicMock()
        with patch("apps.catalogue.search.get_client", return_value=client):
            search.index_product(product)
        doc = self._collection(client).documents.upsert.call_args.args[0]
        assert doc["id"] == str(product.id)
        assert doc["min_price"] == 2.0 and doc["max_price"] == 6.0

    def test_delete_product_swallows_missing(self):
        from typesense.exceptions import ObjectNotFound

        client = MagicMock()
        self._collection(
            client
        ).documents.__getitem__.return_value.delete.side_effect = ObjectNotFound("not found")
        with patch("apps.catalogue.search.get_client", return_value=client):
            search.delete_product("does-not-exist")  # must not raise

    def test_delete_product_reraises_transport_error(self):
        # A real outage must propagate so the Celery task retries it.
        client = MagicMock()
        self._collection(
            client
        ).documents.__getitem__.return_value.delete.side_effect = ConnectionError("typesense down")
        with patch("apps.catalogue.search.get_client", return_value=client):
            with pytest.raises(ConnectionError):
                search.delete_product("some-id")

    def test_search_products_parses_hits_and_total(self):
        client = MagicMock()
        self._collection(client).documents.search.return_value = {
            "found": 2,
            "hits": [{"document": {"id": "one"}}, {"document": {"id": "two"}}],
        }
        with patch("apps.catalogue.search.get_client", return_value=client):
            ids, total = search.search_products(
                "kale", category_slug="veg", min_price="1", max_price="9", featured=True
            )
        assert ids == ["one", "two"]
        assert total == 2
        # Filters are compiled into a single filter_by expression.
        params = self._collection(client).documents.search.call_args.args[0]
        assert "category_slug:=veg" in params["filter_by"]
        assert "is_featured:=true" in params["filter_by"]

    def test_search_products_raises_when_disabled(self):
        with patch("apps.catalogue.search.get_client", return_value=None):
            with pytest.raises(RuntimeError):
                search.search_products("kale")
