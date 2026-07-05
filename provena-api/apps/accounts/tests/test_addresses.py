import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Address, Role, User


@pytest.fixture
def buyer(db):
    return User.objects.create_user(
        email="buyer@example.com", password="Securepass123!", role=Role.BUYER
    )


@pytest.fixture
def other_buyer(db):
    return User.objects.create_user(
        email="other@example.com", password="Securepass123!", role=Role.BUYER
    )


@pytest.fixture
def buyer_client(buyer):
    c = APIClient()
    c.force_authenticate(user=buyer)
    return c


@pytest.fixture
def address(buyer):
    return Address.objects.create(
        user=buyer,
        full_name="Alex Johnson",
        line1="12 Market Street",
        city="London",
        postcode="SW1A 1AA",
        country="GB",
        is_default=True,
    )


@pytest.fixture
def second_address(buyer):
    return Address.objects.create(
        user=buyer,
        full_name="Alex Johnson",
        line1="5 Oak Avenue",
        city="Manchester",
        postcode="M1 1AE",
        country="GB",
        is_default=False,
    )


LIST_URL = "/api/v1/auth/addresses/"


def detail_url(pk):
    return f"/api/v1/auth/addresses/{pk}/"


def default_url(pk):
    return f"/api/v1/auth/addresses/{pk}/default/"


class TestAddressListCreate:
    def test_list_own_addresses(self, buyer_client, address, second_address):
        res = buyer_client.get(LIST_URL)
        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_default_address_listed_first(self, buyer_client, address, second_address):
        res = buyer_client.get(LIST_URL)
        assert res.json()[0]["is_default"] is True

    def test_create_address(self, buyer_client, buyer):
        res = buyer_client.post(
            LIST_URL,
            {
                "full_name": "Sam Smith",
                "line1": "1 High Street",
                "city": "Bristol",
                "postcode": "BS1 1AA",
                "country": "GB",
            },
            format="json",
        )
        assert res.status_code == 201
        assert res.json()["city"] == "Bristol"

    def test_first_address_auto_set_as_default(self, buyer_client, buyer):
        res = buyer_client.post(
            LIST_URL,
            {
                "full_name": "Sam Smith",
                "line1": "1 High Street",
                "city": "Bristol",
                "postcode": "BS1 1AA",
                "country": "GB",
            },
            format="json",
        )
        assert res.json()["is_default"] is True

    def test_create_with_is_default_promotes(self, buyer_client, address):
        res = buyer_client.post(
            LIST_URL,
            {
                "full_name": "Sam Smith",
                "line1": "99 New Road",
                "city": "Leeds",
                "postcode": "LS1 1AA",
                "country": "GB",
                "is_default": True,
            },
            format="json",
        )
        assert res.status_code == 201
        address.refresh_from_db()
        assert address.is_default is False

    def test_postcode_uppercased(self, buyer_client):
        res = buyer_client.post(
            LIST_URL,
            {
                "full_name": "Sam Smith",
                "line1": "1 High Street",
                "city": "Bristol",
                "postcode": "bs1 1aa",
                "country": "GB",
            },
            format="json",
        )
        assert res.json()["postcode"] == "BS1 1AA"

    def test_requires_authentication(self):
        res = APIClient().get(LIST_URL)
        assert res.status_code == 401

    def test_missing_required_field(self, buyer_client):
        res = buyer_client.post(
            LIST_URL,
            {"full_name": "Sam Smith", "line1": "1 High Street", "city": "Bristol"},
            format="json",
        )
        assert res.status_code == 400


class TestAddressDetail:
    def test_update_address(self, buyer_client, address):
        res = buyer_client.patch(detail_url(address.id), {"city": "Edinburgh"}, format="json")
        assert res.status_code == 200
        assert res.json()["city"] == "Edinburgh"

    def test_cannot_update_other_users_address(self, other_buyer, address):
        c = APIClient()
        c.force_authenticate(user=other_buyer)
        res = c.patch(detail_url(address.id), {"city": "Edinburgh"}, format="json")
        assert res.status_code == 404

    def test_delete_address(self, buyer_client, address):
        res = buyer_client.delete(detail_url(address.id))
        assert res.status_code == 204
        assert not Address.objects.filter(pk=address.id).exists()

    def test_delete_default_promotes_next(self, buyer_client, address, second_address):
        buyer_client.delete(detail_url(address.id))
        second_address.refresh_from_db()
        assert second_address.is_default is True

    def test_cannot_delete_other_users_address(self, other_buyer, address):
        c = APIClient()
        c.force_authenticate(user=other_buyer)
        res = c.delete(detail_url(address.id))
        assert res.status_code == 404


class TestAddressSetDefault:
    def test_set_default(self, buyer_client, address, second_address):
        res = buyer_client.post(default_url(second_address.id))
        assert res.status_code == 200
        assert res.json()["is_default"] is True
        address.refresh_from_db()
        assert address.is_default is False

    def test_cannot_set_other_users_address_as_default(self, other_buyer, second_address):
        c = APIClient()
        c.force_authenticate(user=other_buyer)
        res = c.post(default_url(second_address.id))
        assert res.status_code == 404
