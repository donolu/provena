from decimal import Decimal
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.catalogue.models import Category, Product, ProductStatus, ProductVariant
from apps.inventory.models import StockLevel
from apps.orders import services as order_services
from apps.payments import services as payment_services
from apps.suppliers.models import Supplier, SupplierStatus

SHIPPING = {
    "name": "Test Buyer",
    "line1": "1 Test Street",
    "line2": "",
    "city": "London",
    "postcode": "EC1A 1BB",
    "country": "GB",
}

FAKE_INTENT_ID = "pi_test_abc123"
FAKE_CLIENT_SECRET = "pi_test_abc123_secret_xyz"


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
def supplier_client(approved_supplier):
    c = APIClient()
    c.force_authenticate(user=approved_supplier.user)
    return c


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
def placed_order(buyer, variant):
    return order_services.place_order(
        buyer=buyer,
        items=[{"variant": variant, "quantity": 2}],
        shipping=SHIPPING,
    )


@pytest.fixture
def sub_order(placed_order):
    return placed_order.sub_orders.first()


@pytest.fixture
def mock_stripe_services():
    """Patch stripe inside the payments services module."""
    with patch("apps.payments.services.stripe") as mock:
        mock.PaymentIntent.create.return_value = {
            "id": FAKE_INTENT_ID,
            "client_secret": FAKE_CLIENT_SECRET,
        }
        yield mock


@pytest.fixture
def mock_stripe_views():
    """Patch stripe inside the payments views module."""
    with patch("apps.payments.views.stripe") as mock:
        yield mock


@pytest.fixture
def payment(placed_order, mock_stripe_services):
    return payment_services.create_payment_intent(placed_order)


@pytest.fixture
def succeeded_payment(payment):
    return payment_services.handle_payment_succeeded(payment.stripe_payment_intent_id)
