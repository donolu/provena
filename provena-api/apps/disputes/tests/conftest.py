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
        email="buyer@example.com", password="Securepass123!", role=Role.BUYER
    )


@pytest.fixture
def buyer_client(api_client, buyer):
    api_client.force_authenticate(user=buyer)
    return api_client


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@example.com", password="Securepass123!", role=Role.ADMIN, is_staff=True
    )


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def supplier(db):
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
def supplier_client(api_client, supplier):
    api_client.force_authenticate(user=supplier.user)
    return api_client


@pytest.fixture
def category(db):
    return Category.objects.create(name="Vegetables", slug="vegetables", dispute_window_days=3)


@pytest.fixture
def product(db, supplier, category):
    return Product.objects.create(
        supplier=supplier,
        category=category,
        name="Organic Carrots",
        slug="organic-carrots",
        status=ProductStatus.ACTIVE,
    )


@pytest.fixture
def variant(db, product):
    v = ProductVariant.objects.create(
        product=product, name="1kg bag", sku="CARR-1KG-D", price=Decimal("3.99")
    )
    StockLevel.objects.create(variant=v, quantity_available=100)
    return v


@pytest.fixture
def placed_order(db, buyer, variant):
    return order_services.place_order(
        buyer=buyer,
        items=[{"variant": variant, "quantity": 1}],
        shipping=SHIPPING,
    )


@pytest.fixture
def sub_order(placed_order):
    return placed_order.sub_orders.first()


@pytest.fixture
def dispatched_sub_order(sub_order):
    order_services.dispatch_sub_order(sub_order, tracking_number="TRACK-001")
    sub_order.refresh_from_db()
    return sub_order
