"""Dispute-related assertions that live in the orders test suite.

The full dispute feature lives in apps.disputes. These tests only cover
behaviour that is intrinsically part of the orders API (e.g. sub-order fields).
"""

from apps.orders import services


class TestDeliveredAtInSubOrder:
    def test_delivered_at_populated_after_deliver(
        self, buyer_client, placed_order, dispatched_sub_order
    ):
        services.deliver_sub_order(dispatched_sub_order)
        response = buyer_client.get(f"/api/v1/orders/{placed_order.reference}/")
        sub = response.json()["sub_orders"][0]
        assert sub["delivered_at"] is not None
