"""Tests that email_service.py respects NotificationPreference opt-outs."""

from unittest.mock import MagicMock, patch

import pytest

from apps.notifications.email_service import (
    send_order_confirmation_buyer,
    send_order_notification_supplier,
    send_payout_received,
    send_shipping_update,
)
from apps.notifications.models import NotificationPreference


@pytest.fixture
def buyer(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        email="buyer@test.com",
        password="pass1234!",
    )


@pytest.fixture
def supplier_user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        email="supplier@test.com",
        password="pass1234!",
    )


def _make_order(buyer, reference="ORD-001"):
    order = MagicMock()
    order.buyer = buyer
    order.reference = reference
    order.total_amount = "50.00"
    order.shipping_name = "A B"
    order.shipping_line1 = "1 Street"
    order.shipping_line2 = ""
    order.shipping_city = "London"
    order.shipping_postcode = "SW1A 1AA"
    order.sub_orders.select_related.return_value.prefetch_related.return_value = []
    return order


def _make_supplier(user):
    supplier = MagicMock()
    supplier.user = user
    supplier.business_name = "Test Farm"
    return supplier


def _make_sub_order(buyer=None, supplier_user=None):
    supplier = _make_supplier(supplier_user)
    order = _make_order(buyer)
    sub = MagicMock()
    sub.order = order
    sub.supplier = supplier
    sub.subtotal = "25.00"
    sub.tracking_number = None
    sub.items.select_related.return_value.all.return_value = []
    return sub


def _make_payout(supplier_user):
    supplier = _make_supplier(supplier_user)
    payout = MagicMock()
    payout.supplier = supplier
    payout.gross_amount = "50.00"
    payout.platform_fee = "5.00"
    payout.net_amount = "45.00"
    payout.sub_order.order.reference = "ORD-001"
    return payout


class TestSendOrderConfirmationBuyerGating:
    def test_sends_when_opted_in(self, buyer):
        NotificationPreference.objects.create(user=buyer, email_order_placed=True)
        order = _make_order(buyer)
        with patch("apps.notifications.email_service._send") as mock_send:
            send_order_confirmation_buyer(order)
        mock_send.assert_called_once()

    def test_skips_when_opted_out(self, buyer):
        NotificationPreference.objects.create(user=buyer, email_order_placed=False)
        order = _make_order(buyer)
        with patch("apps.notifications.email_service._send") as mock_send:
            send_order_confirmation_buyer(order)
        mock_send.assert_not_called()

    def test_sends_when_no_pref_row_exists(self, buyer):
        order = _make_order(buyer)
        with patch("apps.notifications.email_service._send") as mock_send:
            send_order_confirmation_buyer(order)
        mock_send.assert_called_once()


class TestSendShippingUpdateGating:
    def test_sends_when_opted_in(self, buyer, supplier_user):
        NotificationPreference.objects.create(user=buyer, email_order_dispatched=True)
        sub = _make_sub_order(buyer=buyer, supplier_user=supplier_user)
        with patch("apps.notifications.email_service._send") as mock_send:
            send_shipping_update(sub)
        mock_send.assert_called_once()

    def test_skips_when_opted_out(self, buyer, supplier_user):
        NotificationPreference.objects.create(user=buyer, email_order_dispatched=False)
        sub = _make_sub_order(buyer=buyer, supplier_user=supplier_user)
        with patch("apps.notifications.email_service._send") as mock_send:
            send_shipping_update(sub)
        mock_send.assert_not_called()


class TestSendOrderNotificationSupplierGating:
    def test_sends_when_opted_in(self, buyer, supplier_user):
        NotificationPreference.objects.create(user=supplier_user, email_new_order=True)
        sub = _make_sub_order(buyer=buyer, supplier_user=supplier_user)
        with patch("apps.notifications.email_service._send") as mock_send:
            send_order_notification_supplier(sub)
        mock_send.assert_called_once()

    def test_skips_when_opted_out(self, buyer, supplier_user):
        NotificationPreference.objects.create(user=supplier_user, email_new_order=False)
        sub = _make_sub_order(buyer=buyer, supplier_user=supplier_user)
        with patch("apps.notifications.email_service._send") as mock_send:
            send_order_notification_supplier(sub)
        mock_send.assert_not_called()


class TestSendPayoutReceivedGating:
    def test_sends_when_opted_in(self, supplier_user):
        NotificationPreference.objects.create(user=supplier_user, email_payout_received=True)
        payout = _make_payout(supplier_user)
        with patch("apps.notifications.email_service._send") as mock_send:
            send_payout_received(payout)
        mock_send.assert_called_once()

    def test_skips_when_opted_out(self, supplier_user):
        NotificationPreference.objects.create(user=supplier_user, email_payout_received=False)
        payout = _make_payout(supplier_user)
        with patch("apps.notifications.email_service._send") as mock_send:
            send_payout_received(payout)
        mock_send.assert_not_called()
