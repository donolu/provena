import pytest
from django.core.management import call_command

from apps.accounts.models import User
from apps.catalogue.models import Product
from apps.orders.models import OrderStatus, SubOrder
from apps.suppliers.models import Supplier, SupplierStatus


@pytest.mark.django_db
def test_seed_e2e_data_creates_fixtures_and_is_idempotent():
    call_command("seed_e2e_data")
    # Running again must not duplicate anything.
    call_command("seed_e2e_data")

    # Accounts: buyer (no TOTP), admin + supplier (TOTP enforced), pending supplier.
    assert User.objects.filter(email="e2e-buyer@provena.test", totp_enabled=False).exists()
    assert User.objects.filter(
        email="e2e-admin@provena.test", is_staff=True, totp_enabled=True
    ).exists()
    assert User.objects.filter(email="e2e-supplier@provena.test", totp_enabled=True).exists()

    assert Supplier.objects.filter(
        slug="e2e-test-supplier", status=SupplierStatus.APPROVED
    ).exists()
    assert Supplier.objects.filter(status=SupplierStatus.PENDING).count() == 1

    # Catalogue: the main product plus two related products (for the PDP grid).
    assert Product.objects.filter(slug="e2e-test-product", status="ACTIVE").exists()
    assert Product.objects.filter(slug="e2e-related-product-1").exists()
    assert Product.objects.filter(slug="e2e-related-product-2").exists()

    # A single CONFIRMED sub-order for the approved supplier.
    assert SubOrder.objects.filter(status=OrderStatus.CONFIRMED).count() == 1


@pytest.mark.django_db
def test_seed_e2e_data_accepts_custom_password():
    call_command("seed_e2e_data", "--password", "Custompw123!")
    buyer = User.objects.get(email="e2e-buyer@provena.test")
    assert buyer.check_password("Custompw123!")
