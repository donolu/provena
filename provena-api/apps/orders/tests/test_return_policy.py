"""Return eligibility by product type (ADR-014): the policy is snapshotted onto the OrderItem
at checkout, buyer returns of non-returnable (perishable) items are blocked and steered to a
dispute, and the admin item-refund path stays unrestricted."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.catalogue.models import Category, Product, ProductVariant, ReturnPolicy
from apps.inventory.models import StockLevel
from apps.orders import services
from apps.orders.models import ReturnStatus
from apps.orders.tests.conftest import SHIPPING
from apps.payments.models import Payment, PaymentStatus, Payout, PayoutStatus


def _perishable_variant(supplier, *, policy=ReturnPolicy.DEFECTIVE_ONLY, sku="PERISH-1"):
    cat = Category.objects.create(
        name=f"Cat-{sku}", slug=f"cat-{sku.lower()}", return_policy=policy
    )
    product = Product.objects.create(
        supplier=supplier, category=cat, name=f"Prod-{sku}", slug=f"prod-{sku.lower()}"
    )
    v = ProductVariant.objects.create(product=product, name="unit", sku=sku, price=Decimal("4.00"))
    StockLevel.objects.create(variant=v, quantity_available=100)
    return v


@pytest.mark.django_db
class TestReturnPolicySnapshot:
    def test_returnable_category_snapshots_returnable(self, buyer, variant):
        # The orders `variant` fixture is under a RETURNABLE category.
        order = services.place_order(buyer, [{"variant": variant, "quantity": 1}], SHIPPING)
        item = order.sub_orders.first().items.first()
        assert item.return_policy == ReturnPolicy.RETURNABLE
        assert item.is_returnable is True

    def test_perishable_category_snapshots_defective_only(self, buyer, approved_supplier):
        v = _perishable_variant(approved_supplier)
        order = services.place_order(buyer, [{"variant": v, "quantity": 1}], SHIPPING)
        item = order.sub_orders.first().items.first()
        assert item.return_policy == ReturnPolicy.DEFECTIVE_ONLY
        assert item.is_returnable is False

    def test_sealed_category_snapshots_sealed_and_stays_returnable(self, buyer, approved_supplier):
        # Sealed hygiene goods remain returnable while unopened (supplier verifies the seal).
        v = _perishable_variant(approved_supplier, policy=ReturnPolicy.SEALED, sku="SEALED-1")
        order = services.place_order(buyer, [{"variant": v, "quantity": 1}], SHIPPING)
        item = order.sub_orders.first().items.first()
        assert item.return_policy == ReturnPolicy.SEALED
        assert item.is_returnable is True

    def test_snapshot_frozen_after_category_reclassification(self, buyer, approved_supplier):
        v = _perishable_variant(approved_supplier, policy=ReturnPolicy.RETURNABLE, sku="FROZEN-1")
        order = services.place_order(buyer, [{"variant": v, "quantity": 1}], SHIPPING)
        # Reclassify the category to perishable after the order.
        cat = v.product.category
        cat.return_policy = ReturnPolicy.DEFECTIVE_ONLY
        cat.save(update_fields=["return_policy"])
        item = order.sub_orders.first().items.first()
        item.refresh_from_db()
        assert item.return_policy == ReturnPolicy.RETURNABLE  # unchanged


@pytest.mark.django_db
class TestReturnBlockedForPerishable:
    def _delivered_perishable(self, buyer, supplier):
        v = _perishable_variant(supplier)
        order = services.place_order(buyer, [{"variant": v, "quantity": 2}], SHIPPING)
        sub = order.sub_orders.first()
        services.dispatch_sub_order(sub)
        services.deliver_sub_order(sub)
        return sub

    def test_per_item_return_blocked(self, buyer, approved_supplier):
        sub = self._delivered_perishable(buyer, approved_supplier)
        item = sub.items.first()
        with pytest.raises(ValueError, match="non-returnable"):
            services.request_return(
                sub, buyer, "Changed my mind", items=[{"order_item": item, "quantity": 1}]
            )

    def test_full_return_blocked_when_any_perishable(self, buyer, approved_supplier):
        sub = self._delivered_perishable(buyer, approved_supplier)
        with pytest.raises(ValueError, match="non-returnable"):
            services.request_return(sub, buyer, "Changed my mind")

    def test_no_orphan_return_left_on_block(self, buyer, approved_supplier):
        from apps.orders.models import OrderReturn

        sub = self._delivered_perishable(buyer, approved_supplier)
        with pytest.raises(ValueError):
            services.request_return(sub, buyer, "Changed my mind")
        assert OrderReturn.objects.filter(sub_order=sub).count() == 0

    def test_returnable_item_still_allowed(self, buyer, dispatched_sub_order):
        # The fixture chain uses the RETURNABLE orders category.
        sub = services.deliver_sub_order(dispatched_sub_order)
        ret = services.request_return(sub, buyer, "Faulty")
        assert ret.sub_order_id == sub.id

    def test_sealed_item_return_allowed(self, buyer, approved_supplier):
        # Sealed hygiene goods may still be returned (if unopened); the request is not blocked.
        v = _perishable_variant(approved_supplier, policy=ReturnPolicy.SEALED, sku="SEALED-2")
        order = services.place_order(buyer, [{"variant": v, "quantity": 1}], SHIPPING)
        sub = order.sub_orders.first()
        services.dispatch_sub_order(sub)
        services.deliver_sub_order(sub)
        ret = services.request_return(sub, buyer, "Unopened, changed my mind")
        assert ret.sub_order_id == sub.id


@pytest.mark.django_db
class TestAdminRefundUnrestrictedByPolicy:
    def test_admin_can_refund_perishable_item(self, buyer, approved_supplier):
        v = _perishable_variant(approved_supplier)
        order = services.place_order(buyer, [{"variant": v, "quantity": 1}], SHIPPING)
        Payment.objects.create(
            order=order,
            stripe_payment_intent_id=f"pi_{order.reference}",
            amount=order.total_amount,
            status=PaymentStatus.SUCCEEDED,
        )
        sub = order.sub_orders.first()
        Payout.objects.create(
            sub_order=sub,
            supplier=sub.supplier,
            gross_amount=sub.subtotal,
            platform_fee=Decimal("0.00"),
            net_amount=sub.subtotal,
            status=PayoutStatus.PAID,
            stripe_transfer_id="tr_perish",
        )
        intent = MagicMock()
        intent.latest_charge = "ch_test"
        with (
            patch("stripe.PaymentIntent.retrieve", return_value=intent),
            patch("stripe.Refund.create", return_value=MagicMock(id="re_test")),
            patch("stripe.Transfer.create_reversal", return_value=MagicMock(id="trr_test")),
        ):
            returns = services.admin_refund_order_items(
                order, [{"order_item": sub.items.first(), "quantity": 1}], raised_by=None
            )
        assert returns[0].status == ReturnStatus.REFUNDED
