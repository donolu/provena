from decimal import Decimal

import pytest

from apps.accounts.models import Role, User
from apps.catalogue.models import Category, Product, ProductImage, ProductStatus, ProductVariant
from apps.suppliers.models import Supplier, SupplierStatus


@pytest.fixture
def category(db):
    return Category.objects.create(name="Fresh Produce", slug="fresh-produce")


@pytest.fixture
def subcategory(db, category):
    return Category.objects.create(name="Vegetables", slug="vegetables", parent=category)


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
def active_product(db, approved_supplier, category):
    return Product.objects.create(
        supplier=approved_supplier,
        category=category,
        name="Organic Carrots",
        slug="organic-carrots",
        description="Fresh organic carrots.",
        status=ProductStatus.ACTIVE,
    )


@pytest.fixture
def draft_product(db, approved_supplier, category):
    return Product.objects.create(
        supplier=approved_supplier,
        category=category,
        name="Heritage Tomatoes",
        slug="heritage-tomatoes",
        status=ProductStatus.DRAFT,
    )


@pytest.fixture
def variant(db, active_product):
    return ProductVariant.objects.create(
        product=active_product,
        name="1kg bag",
        sku="CARR-1KG",
        price=Decimal("3.99"),
        weight_grams=1000,
    )


@pytest.fixture
def image(db, active_product):
    return ProductImage.objects.create(
        product=active_product,
        url="https://example.com/carrots.jpg",
        alt_text="Fresh organic carrots",
        position=0,
        is_primary=True,
    )
