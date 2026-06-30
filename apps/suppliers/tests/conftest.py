import pytest

from apps.accounts.models import Role, User
from apps.suppliers.services import create_supplier_profile


@pytest.fixture
def supplier_user(db):
    return User.objects.create_user(
        email="vendor@example.com",
        password="Securepass123!",
        role=Role.SUPPLIER,
    )


@pytest.fixture
def pending_supplier(supplier_user):
    return create_supplier_profile(
        user=supplier_user,
        business_name="Fresh Farms Ltd",
        description="The best fresh produce",
        phone="07700900000",
        address_data={
            "line1": "1 Farm Lane",
            "city": "London",
            "postcode": "E1 1AA",
            "country": "GB",
        },
    )


@pytest.fixture
def approved_supplier(pending_supplier, admin_user):
    from apps.suppliers.services import approve_supplier

    return approve_supplier(pending_supplier, admin_user)


@pytest.fixture
def supplier_user_client(api_client, supplier_user):
    api_client.force_authenticate(user=supplier_user)
    return api_client
