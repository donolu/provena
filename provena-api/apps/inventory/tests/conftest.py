from decimal import Decimal

import pytest

from apps.accounts.models import Role, User
from apps.catalogue.models import Category, Product, ProductStatus, ProductVariant
from apps.inventory.models import StockLevel
from apps.suppliers.models import Supplier, SupplierStatus


@pytest.fixture
def approved_supplier(db):
    user = User.objects.create_user(
        email="farm@example.com", password="Securepass123!", role=Role.SUPPLIER
    )
    return Supplier.objects.create(
        user=user,
        business_name="Green Roots Farm",
        slug="green-roots-farm",
        status=SupplierStatus.APPROVED,
    )


@pytest.fixture
def second_supplier(db):
    user = User.objects.create_user(
        email="other@example.com", password="Securepass123!", role=Role.SUPPLIER
    )
    return Supplier.objects.create(
        user=user,
        business_name="Other Farm",
        slug="other-farm",
        status=SupplierStatus.APPROVED,
    )


@pytest.fixture
def supplier_client(api_client, approved_supplier):
    api_client.force_authenticate(user=approved_supplier.user)
    return api_client


@pytest.fixture
def second_supplier_client(api_client, second_supplier):
    api_client.force_authenticate(user=second_supplier.user)
    return api_client


@pytest.fixture
def category(db):
    return Category.objects.create(name="Vegetables", slug="vegetables")


@pytest.fixture
def product(db, approved_supplier, category):
    return Product.objects.create(
        supplier=approved_supplier,
        category=category,
        name="Organic Carrots",
        slug="organic-carrots",
        status=ProductStatus.ACTIVE,
    )


@pytest.fixture
def variant(db, product):
    return ProductVariant.objects.create(
        product=product,
        name="1kg bag",
        sku="CARR-1KG",
        price=Decimal("3.99"),
        weight_grams=1000,
    )


@pytest.fixture
def second_variant(db, second_supplier, category):
    p = Product.objects.create(
        supplier=second_supplier,
        category=category,
        name="Other Product",
        slug="other-product",
        status=ProductStatus.ACTIVE,
    )
    return ProductVariant.objects.create(
        product=p, name="1kg", sku="OTHER-1KG", price=Decimal("2.00")
    )


@pytest.fixture
def stock_level(db, variant):
    return StockLevel.objects.create(variant=variant, quantity_available=50)
