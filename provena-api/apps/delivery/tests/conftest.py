from decimal import Decimal

import pytest

from apps.accounts.models import Role, User
from apps.catalogue.models import Category, Product, ProductStatus, ProductVariant
from apps.inventory.models import StockLevel
from apps.suppliers.models import FulfilmentMode, Supplier, SupplierStatus

SHIPPING = {
    "name": "Test Buyer",
    "line1": "1 Test Street",
    "line2": "",
    "city": "London",
    "postcode": "EC1A 1BB",
    "country": "GB",
}

UNSERVICEABLE_SHIPPING = {**SHIPPING, "postcode": "ZZ1 1AA"}


@pytest.fixture
def courier_buyer(db):
    return User.objects.create_user(
        email="courier-buyer@example.com", password="Securepass123!", role=Role.BUYER
    )


@pytest.fixture
def platform_supplier(db):
    user = User.objects.create_user(
        email="platform-farm@example.com", password="Securepass123!", role=Role.SUPPLIER
    )
    return Supplier.objects.create(
        user=user,
        business_name="No-Van Farm",
        slug="no-van-farm",
        status=SupplierStatus.APPROVED,
        fulfilment_mode=FulfilmentMode.PLATFORM_DELIVERY,
        stripe_account_id="acct_courier",
        stripe_onboarding_complete=True,
    )


@pytest.fixture
def platform_variant(db, platform_supplier):
    category = Category.objects.create(name="Veg", slug="veg-courier")
    product = Product.objects.create(
        supplier=platform_supplier,
        category=category,
        name="Courier Carrots",
        slug="courier-carrots",
        status=ProductStatus.ACTIVE,
    )
    v = ProductVariant.objects.create(
        product=product, name="1kg", sku="CRR-1KG", price=Decimal("10.00")
    )
    StockLevel.objects.create(variant=v, quantity_available=100)
    return v
