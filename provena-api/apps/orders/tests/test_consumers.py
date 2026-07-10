import json
import secrets

import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.core.cache import cache

from apps.accounts.models import Role, User
from apps.orders.views import WS_TICKET_PREFIX, WS_TICKET_TTL
from config.asgi import application

_ORIGIN_HEADERS = [(b"origin", b"http://localhost")]


def _make_ticket(user: User) -> str:
    ticket = secrets.token_urlsafe(32)
    cache.set(f"{WS_TICKET_PREFIX}{ticket}", str(user.pk), timeout=WS_TICKET_TTL)
    return ticket


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
        ticket = _make_ticket(buyer)
        url = f"/ws/orders/{placed_order.reference}/?ticket={ticket}"
        communicator = _communicator(url)
        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()

    async def test_connect_no_ticket_rejected(self, placed_order):
        url = f"/ws/orders/{placed_order.reference}/"
        communicator = _communicator(url)
        connected, code = await communicator.connect()
        assert not connected
        assert code == 4001

    async def test_connect_wrong_buyer_rejected(self, placed_order, other_buyer):
        ticket = _make_ticket(other_buyer)
        url = f"/ws/orders/{placed_order.reference}/?ticket={ticket}"
        communicator = _communicator(url)
        connected, code = await communicator.connect()
        assert not connected
        assert code == 4003

    async def test_ticket_is_one_time_use(self, placed_order, buyer):
        ticket = _make_ticket(buyer)
        url = f"/ws/orders/{placed_order.reference}/?ticket={ticket}"
        c1 = _communicator(url)
        connected, _ = await c1.connect()
        assert connected
        await c1.disconnect()

        c2 = _communicator(url)
        connected2, code = await c2.connect()
        assert not connected2
        assert code == 4001

    async def test_status_push_received(self, placed_order, buyer, approved_supplier):
        ticket = _make_ticket(buyer)
        url = f"/ws/orders/{placed_order.reference}/?ticket={ticket}"
        communicator = _communicator(url)
        connected, _ = await communicator.connect()
        assert connected

        def _confirm():
            from apps.orders import services

            sub = placed_order.sub_orders.first()
            services.confirm_sub_order(sub)

        await sync_to_async(_confirm)()

        message = await communicator.receive_from(timeout=3)
        data = json.loads(message)
        assert data["type"] == "order_status"
        assert data["status"] == "CONFIRMED"
        await communicator.disconnect()
