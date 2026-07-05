"""Tests for the supplier bulk product upload endpoints."""

import csv
import io

import openpyxl
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.catalogue.models import Category, Product, ProductVariant
from apps.suppliers.models import Supplier


def _csv_bytes(*rows: dict) -> bytes:
    buf = io.StringIO()
    if not rows:
        writer = csv.DictWriter(
            buf,
            fieldnames=[
                "product_name",
                "variant_name",
                "sku",
                "price",
                "description",
                "category",
                "compare_at_price",
                "weight_grams",
                "image_url",
            ],
        )
        writer.writeheader()
    else:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return buf.getvalue().encode()


def _valid_row(**overrides) -> dict:
    base = {
        "product_name": "Organic Carrots",
        "variant_name": "1kg bag",
        "sku": "CARR-1KG",
        "price": "3.99",
        "description": "Fresh carrots",
        "category": "",
        "compare_at_price": "",
        "weight_grams": "1000",
        "image_url": "",
    }
    base.update(overrides)
    return base


@pytest.fixture
def supplier_user(db):
    user = User.objects.create_user(
        email="supplier@example.com", password="Securepass123!", role=Role.SUPPLIER
    )
    Supplier.objects.create(
        user=user,
        business_name="Test Farm",
        slug="test-farm",
        status="APPROVED",
    )
    return user


@pytest.fixture
def supplier_client(supplier_user):
    c = APIClient()
    c.force_authenticate(user=supplier_user)
    return c


@pytest.fixture
def category(db):
    return Category.objects.create(name="Fresh Produce", slug="fresh-produce", is_active=True)


TEMPLATE_URL = "/api/v1/catalogue/products/upload/template/"
PREVIEW_URL = "/api/v1/catalogue/products/upload/preview/"
CONFIRM_URL = "/api/v1/catalogue/products/upload/confirm/"


class TestTemplateDownload:
    def test_returns_csv_file(self, supplier_client):
        res = supplier_client.get(TEMPLATE_URL)
        assert res.status_code == 200
        assert "text/csv" in res["Content-Type"]
        assert "attachment" in res["Content-Disposition"]
        assert "provena_products_template.csv" in res["Content-Disposition"]

    def test_contains_required_headers(self, supplier_client):
        res = supplier_client.get(TEMPLATE_URL)
        first_line = res.content.decode().splitlines()[0]
        for col in ("product_name", "variant_name", "sku", "price"):
            assert col in first_line

    def test_requires_approved_supplier(self, db):
        buyer = User.objects.create_user(
            email="buyer@example.com", password="Securepass123!", role=Role.BUYER
        )
        c = APIClient()
        c.force_authenticate(user=buyer)
        res = c.get(TEMPLATE_URL)
        assert res.status_code == 403


class TestUploadPreview:
    def test_valid_csv_returns_products(self, supplier_client):
        content = _csv_bytes(_valid_row())
        res = supplier_client.post(PREVIEW_URL, {"file": io.BytesIO(content)}, format="multipart")
        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is True
        assert data["product_count"] == 1
        assert data["row_count"] == 1
        assert data["products"][0]["name"] == "Organic Carrots"

    def test_multiple_variants_grouped(self, supplier_client):
        rows = [
            _valid_row(sku="CARR-1KG", variant_name="1kg bag"),
            _valid_row(sku="CARR-500G", variant_name="500g bag", price="2.19"),
        ]
        content = _csv_bytes(*rows)
        res = supplier_client.post(PREVIEW_URL, {"file": io.BytesIO(content)}, format="multipart")
        data = res.json()
        assert data["valid"] is True
        assert data["product_count"] == 1
        assert len(data["products"][0]["variants"]) == 2

    def test_category_resolved(self, supplier_client, category):
        content = _csv_bytes(_valid_row(category="Fresh Produce"))
        res = supplier_client.post(PREVIEW_URL, {"file": io.BytesIO(content)}, format="multipart")
        data = res.json()
        assert data["valid"] is True
        assert data["products"][0]["category"] == "Fresh Produce"

    def test_missing_required_field_returns_error(self, supplier_client):
        row = _valid_row()
        del row["price"]
        content = _csv_bytes(row)
        res = supplier_client.post(PREVIEW_URL, {"file": io.BytesIO(content)}, format="multipart")
        data = res.json()
        assert data["valid"] is False
        assert any(e["column"] == "price" for e in data["errors"])

    def test_invalid_price_returns_error(self, supplier_client):
        content = _csv_bytes(_valid_row(price="not-a-number"))
        res = supplier_client.post(PREVIEW_URL, {"file": io.BytesIO(content)}, format="multipart")
        data = res.json()
        assert data["valid"] is False

    def test_zero_price_returns_error(self, supplier_client):
        content = _csv_bytes(_valid_row(price="0"))
        res = supplier_client.post(PREVIEW_URL, {"file": io.BytesIO(content)}, format="multipart")
        assert res.json()["valid"] is False

    def test_compare_at_price_less_than_price_error(self, supplier_client):
        content = _csv_bytes(_valid_row(compare_at_price="1.00"))
        res = supplier_client.post(PREVIEW_URL, {"file": io.BytesIO(content)}, format="multipart")
        assert res.json()["valid"] is False

    def test_duplicate_sku_in_file(self, supplier_client):
        rows = [_valid_row(sku="DUPE"), _valid_row(sku="DUPE", variant_name="500g bag")]
        content = _csv_bytes(*rows)
        res = supplier_client.post(PREVIEW_URL, {"file": io.BytesIO(content)}, format="multipart")
        assert res.json()["valid"] is False

    def test_existing_sku_in_db(self, supplier_client, supplier_user):
        product = Product.objects.create(
            supplier=supplier_user.supplier,
            name="Old Product",
            slug="old-product",
        )
        ProductVariant.objects.create(product=product, name="1kg", sku="EXISTING", price="1.00")
        content = _csv_bytes(_valid_row(sku="EXISTING"))
        res = supplier_client.post(PREVIEW_URL, {"file": io.BytesIO(content)}, format="multipart")
        assert res.json()["valid"] is False

    def test_empty_file_returns_400(self, supplier_client):
        content = _csv_bytes()
        res = supplier_client.post(PREVIEW_URL, {"file": io.BytesIO(content)}, format="multipart")
        assert res.status_code == 400

    def test_no_file_returns_400(self, supplier_client):
        res = supplier_client.post(PREVIEW_URL, {}, format="multipart")
        assert res.status_code == 400

    def test_xlsx_detected_by_magic_bytes(self, supplier_client):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(
            [
                "product_name",
                "variant_name",
                "sku",
                "price",
                "description",
                "category",
                "compare_at_price",
                "weight_grams",
                "image_url",
            ]
        )
        ws.append(["Tomatoes", "250g", "TOM-250", "1.49", "", "", "", "", ""])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        res = supplier_client.post(PREVIEW_URL, {"file": buf}, format="multipart")
        data = res.json()
        assert data["valid"] is True
        assert data["products"][0]["name"] == "Tomatoes"

    def test_invalid_image_url(self, supplier_client):
        content = _csv_bytes(_valid_row(image_url="not-a-url"))
        res = supplier_client.post(PREVIEW_URL, {"file": io.BytesIO(content)}, format="multipart")
        assert res.json()["valid"] is False


class TestUploadConfirm:
    def test_creates_products_and_variants(self, supplier_client):
        content = _csv_bytes(_valid_row())
        res = supplier_client.post(CONFIRM_URL, {"file": io.BytesIO(content)}, format="multipart")
        assert res.status_code == 201
        assert res.json()["created"] == 1
        assert Product.objects.filter(name="Organic Carrots").exists()
        assert ProductVariant.objects.filter(sku="CARR-1KG").exists()

    def test_products_created_as_draft(self, supplier_client):
        content = _csv_bytes(_valid_row())
        supplier_client.post(CONFIRM_URL, {"file": io.BytesIO(content)}, format="multipart")
        assert Product.objects.get(name="Organic Carrots").status == "DRAFT"

    def test_category_assigned(self, supplier_client, category):
        content = _csv_bytes(_valid_row(category="fresh produce"))
        supplier_client.post(CONFIRM_URL, {"file": io.BytesIO(content)}, format="multipart")
        product = Product.objects.get(name="Organic Carrots")
        assert product.category == category

    def test_image_created(self, supplier_client):
        content = _csv_bytes(_valid_row(image_url="https://example.com/img.jpg"))
        supplier_client.post(CONFIRM_URL, {"file": io.BytesIO(content)}, format="multipart")
        product = Product.objects.get(name="Organic Carrots")
        assert product.images.filter(is_primary=True).exists()

    def test_validation_errors_return_422(self, supplier_client):
        content = _csv_bytes(_valid_row(price="0"))
        res = supplier_client.post(CONFIRM_URL, {"file": io.BytesIO(content)}, format="multipart")
        assert res.status_code == 422
        assert Product.objects.count() == 0

    def test_multi_variant_product(self, supplier_client):
        rows = [
            _valid_row(sku="CARR-1KG", variant_name="1kg"),
            _valid_row(sku="CARR-500G", variant_name="500g", price="2.19"),
        ]
        content = _csv_bytes(*rows)
        res = supplier_client.post(CONFIRM_URL, {"file": io.BytesIO(content)}, format="multipart")
        assert res.status_code == 201
        assert Product.objects.count() == 1
        assert ProductVariant.objects.count() == 2
