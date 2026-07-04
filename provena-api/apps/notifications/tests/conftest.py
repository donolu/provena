import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def buyer(db):
    return User.objects.create_user(
        email="buyer@example.com",
        password="pass1234!",
        first_name="Bob",
        last_name="Buyer",
    )


@pytest.fixture
def buyer_client(buyer):
    client = APIClient()
    client.force_authenticate(user=buyer)
    return client


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="staff@example.com",
        password="pass1234!",
        first_name="Steph",
        last_name="Staff",
        is_staff=True,
    )


@pytest.fixture
def staff_client(staff_user):
    client = APIClient()
    client.force_authenticate(user=staff_user)
    return client
