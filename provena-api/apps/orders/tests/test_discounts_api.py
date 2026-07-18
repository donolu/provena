from decimal import Decimal

import pytest

from apps.orders.models import DiscountCode, DiscountType


def _add_to_cart(buyer, variant, qty=10):
    from apps.marketplace.models import Cart, CartItem

    cart, _ = Cart.objects.get_or_create(buyer=buyer)
    CartItem.objects.create(cart=cart, variant=variant, quantity=qty)


@pytest.mark.django_db
class TestValidateDiscount:
    URL = "/api/v1/discounts/validate/"

    def test_valid_code_returns_amount(self, buyer_client, buyer, variant):
        DiscountCode.objects.create(
            code="SAVE10", discount_type=DiscountType.PERCENTAGE, value=Decimal("10")
        )
        _add_to_cart(buyer, variant, qty=10)  # goods = 3.99 * 10 = 39.90
        res = buyer_client.post(self.URL, {"code": "save10"}, format="json")
        assert res.status_code == 200
        assert res.data["valid"] is True
        assert res.data["code"] == "SAVE10"
        assert res.data["discount_amount"] == "3.99"  # 10% of 39.90
        # new_total is the full pricing pass: goods - discount + shipping (£0 by default).
        assert res.data["new_total"] == "35.91"

    def test_new_total_includes_shipping(self, buyer_client, buyer, variant):
        from apps.suppliers.models import ShippingPolicy

        supplier = variant.product.supplier
        supplier.shipping_policy = ShippingPolicy.FLAT
        supplier.shipping_flat_rate = Decimal("4.50")
        supplier.save(update_fields=["shipping_policy", "shipping_flat_rate"])
        DiscountCode.objects.create(
            code="SAVE10", discount_type=DiscountType.PERCENTAGE, value=Decimal("10")
        )
        _add_to_cart(buyer, variant, qty=10)  # goods = 39.90, discount 3.99
        res = buyer_client.post(self.URL, {"code": "save10"}, format="json")
        assert res.data["valid"] is True
        assert res.data["discount_amount"] == "3.99"
        # 39.90 - 3.99 + 4.50 shipping = 40.41 (VAT is inclusive, so it does not add on top).
        assert res.data["new_total"] == "40.41"

    def test_unknown_code_returns_reason(self, buyer_client, buyer, variant):
        _add_to_cart(buyer, variant)
        res = buyer_client.post(self.URL, {"code": "NOPE"}, format="json")
        assert res.status_code == 200
        assert res.data["valid"] is False
        assert "not found" in res.data["reason"].lower()

    def test_minimum_spend_returns_reason(self, buyer_client, buyer, variant):
        DiscountCode.objects.create(
            code="BIG",
            discount_type=DiscountType.PERCENTAGE,
            value=Decimal("10"),
            minimum_spend=Decimal("100.00"),
        )
        _add_to_cart(buyer, variant, qty=1)
        res = buyer_client.post(self.URL, {"code": "BIG"}, format="json")
        assert res.data["valid"] is False
        assert "spend at least" in res.data["reason"].lower()

    def test_empty_cart_returns_reason(self, buyer_client):
        DiscountCode.objects.create(
            code="SAVE10", discount_type=DiscountType.PERCENTAGE, value=Decimal("10")
        )
        res = buyer_client.post(self.URL, {"code": "SAVE10"}, format="json")
        assert res.data["valid"] is False
        assert "empty" in res.data["reason"].lower()

    def test_requires_auth(self, api_client):
        res = api_client.post(self.URL, {"code": "X"}, format="json")
        assert res.status_code in (401, 403)


@pytest.mark.django_db
class TestAdminDiscountCodes:
    URL = "/api/v1/discounts/admin/"

    def test_admin_can_create_uppercased(self, admin_client):
        res = admin_client.post(
            self.URL,
            {"code": "new5", "discount_type": "FIXED", "value": "5.00", "funded_by": "PLATFORM"},
            format="json",
        )
        assert res.status_code == 201
        assert res.data["code"] == "NEW5"
        assert res.data["times_used"] == 0

    def test_admin_can_list(self, admin_client):
        DiscountCode.objects.create(code="A", discount_type=DiscountType.FIXED, value=Decimal("1"))
        res = admin_client.get(self.URL)
        assert res.status_code == 200

    def test_admin_can_deactivate(self, admin_client):
        code = DiscountCode.objects.create(
            code="OFF", discount_type=DiscountType.FIXED, value=Decimal("5")
        )
        res = admin_client.patch(f"{self.URL}{code.id}/", {"is_active": False}, format="json")
        assert res.status_code == 200
        code.refresh_from_db()
        assert code.is_active is False

    def test_percentage_over_100_rejected(self, admin_client):
        res = admin_client.post(
            self.URL,
            {"code": "BIG", "discount_type": "PERCENTAGE", "value": "150"},
            format="json",
        )
        assert res.status_code == 400

    def test_non_admin_forbidden(self, buyer_client):
        assert buyer_client.get(self.URL).status_code == 403
