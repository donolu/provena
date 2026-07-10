import json

import pytest
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import Role, User
from config.asgi import application

_ORIGIN_HEADERS = [(b"origin", b"http://localhost")]


def _make_token(user: User) -> str:
    return str(AccessToken.for_user(user))


def _communicator(url: str) -> WebsocketCommunicator:
    return WebsocketCommunicator(application, url, headers=_ORIGIN_HEADERS)


@pytest.fixture
def buyer(db):
    return User.objects.create_user(
        email="ws_buyer@example.com",
        password="Securepass123!",
        role=Role.BUYER,
    )


@pytest.fixture
def other_buyer(db):
    return User.objects.create_user(
        email="ws_other@example.com",
        password="Securepass123!",
        role=Role.BUYER,
    )


@pytest.fixture
def placed_order(buyer, approved_supplier, variant):
    from apps.orders import services

    return services.place_order(
        buyer=buyer,
        items=[{"variant": variant, "quantity": 1}],
        shipping={
            "name": "Test",
            "line1": "1 Street",
            "line2": "",
            "city": "London",
            "postcode": "EC1A 1BB",
            "country": "GB",
        },
    )


@pytest.mark.django_db(transaction=True)
class TestOrderStatusConsumer:
    async def test_connect_authenticated_owner(self, placed_order, buyer):
        token = _make_token(buyer)
        url = f"/ws/orders/{placed_order.reference}/?token={token}"
        communicator = _communicator(url)
        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()

    async def test_connect_no_token_rejected(self, placed_order):
        url = f"/ws/orders/{placed_order.reference}/"
        communicator = _communicator(url)
        connected, code = await communicator.connect()
        assert not connected
        assert code == 4001

    async def test_connect_wrong_buyer_rejected(self, placed_order, other_buyer):
        token = _make_token(other_buyer)
        url = f"/ws/orders/{placed_order.reference}/?token={token}"
        communicator = _communicator(url)
        connected, code = await communicator.connect()
        assert not connected
        assert code == 4003

    async def test_status_push_received(self, placed_order, buyer, approved_supplier):
        from asgiref.sync import sync_to_async

        from apps.orders import services

        token = _make_token(buyer)
        url = f"/ws/orders/{placed_order.reference}/?token={token}"
        communicator = _communicator(url)
        connected, _ = await communicator.connect()
        assert connected

        def _confirm():
            sub = placed_order.sub_orders.first()
            services.confirm_sub_order(sub)

        await sync_to_async(_confirm)()

        message = await communicator.receive_from(timeout=3)
        data = json.loads(message)
        assert data["type"] == "order_status"
        assert data["status"] == "CONFIRMED"
        await communicator.disconnect()
