import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def buyer(db):
    return User.objects.create_user(
        email="buyer@example.com",
        password="Securepass123!",  # noqa: S106  # nosec B106
        first_name="Test",
        last_name="Buyer",
        role=Role.BUYER,
    )


@pytest.fixture
def supplier(db):
    return User.objects.create_user(
        email="supplier@example.com",
        password="Securepass123!",  # noqa: S106  # nosec B106
        first_name="Test",
        last_name="Supplier",
        role=Role.SUPPLIER,
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@example.com",
        password="Securepass123!",  # noqa: S106  # nosec B106
        first_name="Test",
        last_name="Admin",
        role=Role.ADMIN,
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def buyer_client(api_client, buyer):
    api_client.force_authenticate(user=buyer)
    return api_client


@pytest.fixture
def supplier_client(api_client, supplier):
    api_client.force_authenticate(user=supplier)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client
