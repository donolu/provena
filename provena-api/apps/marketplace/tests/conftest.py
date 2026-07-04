from decimal import Decimal

import pytest
from rest_framework.test import APIClient

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
def buyer_client(buyer):
    c = APIClient()
    c.force_authenticate(user=buyer)
    return c


@pytest.fixture
def second_buyer(db):
    return User.objects.create_user(
        email="buyer2@example.com",
        password="Securepass123!",
        role=Role.BUYER,
    )


@pytest.fixture
def second_buyer_client(second_buyer):
    c = APIClient()
    c.force_authenticate(user=second_buyer)
    return c


@pytest.fixture
def approved_supplier(db):
    user = User.objects.create_user(
        email="supplier@example.com",
        password="Securepass123!",
        role=Role.SUPPLIER,
    )
    return Supplier.objects.create(
        user=user,
        business_name="Green Roots Farm",
        slug="green-roots-farm",
        status=SupplierStatus.APPROVED,
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name="Vegetables", slug="vegetables")


@pytest.fixture
def product(approved_supplier, category):
    return Product.objects.create(
        supplier=approved_supplier,
        category=category,
        name="Organic Carrots",
        slug="organic-carrots",
        status=ProductStatus.ACTIVE,
    )


@pytest.fixture
def variant(product):
    v = ProductVariant.objects.create(
        product=product,
        name="1kg bag",
        sku="CARR-1KG",
        price=Decimal("2.50"),
        weight_grams=1000,
    )
    StockLevel.objects.create(variant=v, quantity_available=100)
    return v


@pytest.fixture
def second_variant(product):
    v = ProductVariant.objects.create(
        product=product,
        name="2kg bag",
        sku="CARR-2KG",
        price=Decimal("4.50"),
        weight_grams=2000,
    )
    StockLevel.objects.create(variant=v, quantity_available=100)
    return v


@pytest.fixture
def delivered_order(buyer, variant):
    """An order where the buyer has a delivered sub-order for `variant`."""
    order = order_services.place_order(
        buyer=buyer,
        items=[{"variant": variant, "quantity": 1}],
        shipping=SHIPPING,
    )
    sub = order.sub_orders.first()
    order_services.dispatch_sub_order(sub)
    order_services.deliver_sub_order(sub)
    return order


@pytest.fixture
def second_delivered_order(second_buyer, variant):
    """An order where second_buyer has a delivered sub-order for `variant`."""
    order = order_services.place_order(
        buyer=second_buyer,
        items=[{"variant": variant, "quantity": 1}],
        shipping=SHIPPING,
    )
    sub = order.sub_orders.first()
    order_services.dispatch_sub_order(sub)
    order_services.deliver_sub_order(sub)
    return order
