from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.catalogue.models import Category, Product, ProductStatus, ProductVariant
from apps.inventory.models import StockLevel
from apps.orders.models import Order, OrderItem, OrderStatus, SubOrder
from apps.payments.models import Payment, PaymentStatus, Payout, PayoutStatus
from apps.suppliers.models import Supplier, SupplierStatus

User = get_user_model()


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@example.com",
        password="pass1234!",
        first_name="Admin",
        last_name="User",
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def buyer(db):
    return User.objects.create_user(
        email="buyer@example.com", password="pass1234!", first_name="Bob", last_name="Buyer"
    )


@pytest.fixture
def supplier_user(db):
    return User.objects.create_user(
        email="supplier@example.com", password="pass1234!", first_name="Sue", last_name="Supplier"
    )


@pytest.fixture
def approved_supplier(supplier_user):
    return Supplier.objects.create(
        user=supplier_user,
        business_name="Fresh Farms",
        slug="fresh-farms",
        status=SupplierStatus.APPROVED,
    )


@pytest.fixture
def supplier_client(supplier_user):
    client = APIClient()
    client.force_authenticate(user=supplier_user)
    return client


@pytest.fixture
def category(db):
    return Category.objects.create(name="Produce", slug="produce")


@pytest.fixture
def product(approved_supplier, category):
    return Product.objects.create(
        supplier=approved_supplier,
        category=category,
        name="Carrots",
        status=ProductStatus.ACTIVE,
    )


@pytest.fixture
def variant(product):
    v = ProductVariant.objects.create(
        product=product, name="1kg", sku="CARR-1KG", price=Decimal("2.50")
    )
    StockLevel.objects.create(variant=v, quantity_available=100)
    return v


@pytest.fixture
def placed_order(buyer, approved_supplier, variant):
    order = Order.objects.create(
        buyer=buyer, status=OrderStatus.CONFIRMED, total_amount=Decimal("5.00")
    )
    sub = SubOrder.objects.create(
        order=order,
        supplier=approved_supplier,
        status=OrderStatus.CONFIRMED,
        subtotal=Decimal("5.00"),
    )
    OrderItem.objects.create(
        sub_order=sub,
        variant=variant,
        product_name="Carrots",
        variant_name="1kg",
        sku="CARR-1KG",
        quantity=2,
        unit_price=Decimal("2.50"),
    )
    order.total_amount = Decimal("5.00")
    order.save()
    return order


@pytest.fixture
def succeeded_payment(placed_order):
    return Payment.objects.create(
        order=placed_order,
        stripe_payment_intent_id="pi_test_001",
        stripe_client_secret="secret",
        amount=Decimal("5.00"),
        currency="gbp",
        status=PaymentStatus.SUCCEEDED,
    )


@pytest.fixture
def payout(placed_order, approved_supplier):
    sub = placed_order.sub_orders.first()
    return Payout.objects.create(
        sub_order=sub,
        supplier=approved_supplier,
        gross_amount=Decimal("5.00"),
        platform_fee=Decimal("0.50"),
        net_amount=Decimal("4.50"),
        status=PayoutStatus.PENDING,
    )


@pytest.fixture
def today() -> date:
    return date.today()
