"""Tests for cart-level stock reservations (INV-07)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.inventory.models import StockLevel
from apps.marketplace import services
from apps.marketplace.models import CartItem, CartReservation
from apps.marketplace.tasks import release_expired_cart_reservations


def stock(variant) -> StockLevel:
    return StockLevel.objects.get(variant=variant)


class TestAddToCartReservation:
    def test_reserves_stock_on_add(self, buyer, variant):
        services.add_to_cart(user=buyer, variant_id=variant.id, quantity=3)
        s = stock(variant)
        assert s.quantity_available == 97
        assert s.quantity_reserved == 3

    def test_creates_reservation_record(self, buyer, variant):
        item = services.add_to_cart(user=buyer, variant_id=variant.id, quantity=3)
        res = CartReservation.objects.get(cart_item=item)
        assert res.quantity == 3
        assert res.expires_at > timezone.now()

    def test_reservation_expires_in_30_minutes(self, buyer, variant):
        item = services.add_to_cart(user=buyer, variant_id=variant.id, quantity=1)
        res = CartReservation.objects.get(cart_item=item)
        delta = res.expires_at - timezone.now()
        assert timedelta(minutes=29) < delta <= timedelta(minutes=30)

    def test_increments_reserve_existing_item(self, buyer, variant):
        services.add_to_cart(user=buyer, variant_id=variant.id, quantity=2)
        services.add_to_cart(user=buyer, variant_id=variant.id, quantity=3)
        s = stock(variant)
        assert s.quantity_reserved == 5
        assert s.quantity_available == 95

    def test_increments_reservation_quantity_on_readd(self, buyer, variant):
        item = services.add_to_cart(user=buyer, variant_id=variant.id, quantity=2)
        services.add_to_cart(user=buyer, variant_id=variant.id, quantity=3)
        item.refresh_from_db()
        res = CartReservation.objects.get(cart_item=item)
        assert res.quantity == 5

    def test_raises_when_insufficient_stock(self, buyer, variant):
        with pytest.raises(ValueError, match="Insufficient stock"):
            services.add_to_cart(user=buyer, variant_id=variant.id, quantity=200)


class TestUpdateCartItemReservation:
    def test_reserves_delta_when_increasing(self, buyer, variant):
        item = services.add_to_cart(user=buyer, variant_id=variant.id, quantity=3)
        services.update_cart_item(user=buyer, item_id=item.id, quantity=7)
        s = stock(variant)
        assert s.quantity_reserved == 7
        assert s.quantity_available == 93

    def test_releases_delta_when_decreasing(self, buyer, variant):
        item = services.add_to_cart(user=buyer, variant_id=variant.id, quantity=5)
        services.update_cart_item(user=buyer, item_id=item.id, quantity=2)
        s = stock(variant)
        assert s.quantity_reserved == 2
        assert s.quantity_available == 98

    def test_updates_reservation_record(self, buyer, variant):
        item = services.add_to_cart(user=buyer, variant_id=variant.id, quantity=5)
        services.update_cart_item(user=buyer, item_id=item.id, quantity=2)
        res = CartReservation.objects.get(cart_item=item)
        assert res.quantity == 2

    def test_refreshes_expiry_on_update(self, buyer, variant):
        item = services.add_to_cart(user=buyer, variant_id=variant.id, quantity=1)
        original_expiry = CartReservation.objects.get(cart_item=item).expires_at
        services.update_cart_item(user=buyer, item_id=item.id, quantity=2)
        new_expiry = CartReservation.objects.get(cart_item=item).expires_at
        assert new_expiry >= original_expiry


class TestRemoveFromCartReservation:
    def test_releases_stock_on_remove(self, buyer, variant):
        item = services.add_to_cart(user=buyer, variant_id=variant.id, quantity=4)
        services.remove_from_cart(user=buyer, item_id=item.id)
        s = stock(variant)
        assert s.quantity_reserved == 0
        assert s.quantity_available == 100

    def test_deletes_reservation_record(self, buyer, variant):
        item = services.add_to_cart(user=buyer, variant_id=variant.id, quantity=4)
        item_id = item.id
        services.remove_from_cart(user=buyer, item_id=item.id)
        assert CartReservation.objects.filter(cart_item_id=item_id).count() == 0


class TestClearCartReservation:
    def test_releases_all_reservations(self, buyer, variant, second_variant):
        services.add_to_cart(user=buyer, variant_id=variant.id, quantity=2)
        services.add_to_cart(user=buyer, variant_id=second_variant.id, quantity=3)
        services.clear_cart(user=buyer)
        assert stock(variant).quantity_reserved == 0
        assert stock(second_variant).quantity_reserved == 0

    def test_removes_all_cart_items(self, buyer, variant):
        services.add_to_cart(user=buyer, variant_id=variant.id, quantity=1)
        services.clear_cart(user=buyer)
        assert CartItem.objects.filter(cart__buyer=buyer).count() == 0


class TestReleaseExpiredTask:
    def test_releases_expired_reservations(self, buyer, variant):
        item = services.add_to_cart(user=buyer, variant_id=variant.id, quantity=5)
        CartReservation.objects.filter(cart_item=item).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        released = release_expired_cart_reservations()
        assert released == 1
        s = stock(variant)
        assert s.quantity_reserved == 0
        assert s.quantity_available == 100

    def test_removes_cart_item_on_expiry(self, buyer, variant):
        item = services.add_to_cart(user=buyer, variant_id=variant.id, quantity=1)
        CartReservation.objects.filter(cart_item=item).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        release_expired_cart_reservations()
        assert CartItem.objects.filter(id=item.id).count() == 0

    def test_does_not_release_valid_reservations(self, buyer, variant):
        services.add_to_cart(user=buyer, variant_id=variant.id, quantity=3)
        released = release_expired_cart_reservations()
        assert released == 0
        assert stock(variant).quantity_reserved == 3


class TestPlaceOrderConsumesCartReservation:
    SHIPPING = {
        "name": "A B",
        "line1": "1 St",
        "line2": "",
        "city": "London",
        "postcode": "EC1A 1BB",
        "country": "GB",
    }

    def test_does_not_double_reserve_when_cart_reservation_exists(self, buyer, variant):
        from apps.orders import services as order_services

        services.add_to_cart(user=buyer, variant_id=variant.id, quantity=5)
        assert stock(variant).quantity_reserved == 5
        assert stock(variant).quantity_available == 95

        order_services.place_order(
            buyer=buyer,
            items=[{"variant": variant, "quantity": 5}],
            shipping=self.SHIPPING,
        )
        s = stock(variant)
        assert s.quantity_reserved == 5
        assert s.quantity_available == 95

    def test_removes_cart_reservation_and_item_on_checkout(self, buyer, variant):
        from apps.orders import services as order_services

        item = services.add_to_cart(user=buyer, variant_id=variant.id, quantity=2)
        order_services.place_order(
            buyer=buyer,
            items=[{"variant": variant, "quantity": 2}],
            shipping=self.SHIPPING,
        )
        assert CartItem.objects.filter(id=item.id).count() == 0
        assert CartReservation.objects.filter(cart_item_id=item.id).count() == 0

    def test_re_reserves_when_no_cart_reservation(self, buyer, variant):
        from apps.orders import services as order_services

        assert stock(variant).quantity_reserved == 0
        order_services.place_order(
            buyer=buyer,
            items=[{"variant": variant, "quantity": 3}],
            shipping=self.SHIPPING,
        )
        assert stock(variant).quantity_reserved == 3

    def test_re_reserves_when_cart_reservation_expired(self, buyer, variant):
        from apps.orders import services as order_services

        item = services.add_to_cart(user=buyer, variant_id=variant.id, quantity=3)
        CartReservation.objects.filter(cart_item=item).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        from apps.inventory import services as inv_services

        inv_services.release_reservation(variant, 3, reference="CART_EXPIRED")
        CartReservation.objects.filter(cart_item=item).delete()

        order_services.place_order(
            buyer=buyer,
            items=[{"variant": variant, "quantity": 3}],
            shipping=self.SHIPPING,
        )
        assert stock(variant).quantity_reserved == 3
