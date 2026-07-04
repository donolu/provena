from decimal import Decimal

import pytest

from apps.accounts.models import Role, User
from apps.catalogue.models import Category, Product, ProductStatus, ProductVariant
from apps.inventory.models import StockLevel
from apps.orders import services as order_services
from apps.suppliers.models import Supplier, SupplierStatus

SHIPPING = {
    "name": "Test Buyer",
    "line1": "1 Test Street",
    "line2": "",
    "city": "London",
    "postcode": "EC1A 1BB",
    "country": "GB",
}


@pytest.fixture
def buyer(db):
    return User.objects.create_user(
        email="buyer@example.com",
        password="Securepass123!",
        role=Role.BUYER,
    )


@pytest.fixture
def buyer_client(api_client, buyer):
    api_client.force_authenticate(user=buyer)
    return api_client


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
    v = ProductVariant.objects.create(
        product=product,
        name="1kg bag",
        sku="CARR-1KG",
        price=Decimal("3.99"),
        weight_grams=1000,
    )
    StockLevel.objects.create(variant=v, quantity_available=100)
    return v


@pytest.fixture
def second_product(db, second_supplier, category):
    return Product.objects.create(
        supplier=second_supplier,
        category=category,
        name="Heritage Tomatoes",
        slug="heritage-tomatoes",
        status=ProductStatus.ACTIVE,
    )


@pytest.fixture
def second_variant(db, second_product):
    v = ProductVariant.objects.create(
        product=second_product,
        name="500g punnet",
        sku="TOM-500G",
        price=Decimal("2.50"),
    )
    StockLevel.objects.create(variant=v, quantity_available=100)
    return v


@pytest.fixture
def placed_order(db, buyer, variant):
    return order_services.place_order(
        buyer=buyer,
        items=[{"variant": variant, "quantity": 2}],
        shipping=SHIPPING,
    )


@pytest.fixture
def sub_order(placed_order):
    return placed_order.sub_orders.first()


@pytest.fixture
def dispatched_sub_order(sub_order):
    from apps.orders import services

    services.dispatch_sub_order(sub_order, tracking_number="TRACK-001")
    sub_order.refresh_from_db()
    return sub_order
