import pytest

from apps.accounts.models import Role
from apps.suppliers.models import DocumentStatus, DocumentType, SupplierStatus
from apps.suppliers.services import (
    approve_supplier,
    create_supplier_profile,
    reject_supplier,
    review_document,
    set_commission_rate,
    suspend_supplier,
    update_supplier_profile,
    upload_document,
)


@pytest.mark.django_db
class TestCreateSupplierProfile:
    def test_creates_supplier_with_correct_fields(self, supplier_user):
        s = create_supplier_profile(
            user=supplier_user,
            business_name="Green Valley Farm",
            description="Organic produce",
            phone="07700900001",
        )
        assert s.business_name == "Green Valley Farm"
        assert s.description == "Organic produce"
        assert s.status == SupplierStatus.PENDING

    def test_sets_user_role_to_supplier(self, db):
        from apps.accounts.models import User

        user = User.objects.create_user(email="newvendor@example.com", password="Securepass123!")
        assert user.role == Role.BUYER
        create_supplier_profile(user=user, business_name="New Vendor")
        user.refresh_from_db()
        assert user.role == Role.SUPPLIER

    def test_creates_address_when_provided(self, supplier_user):
        s = create_supplier_profile(
            user=supplier_user,
            business_name="Farm With Address",
            address_data={"line1": "99 Rural Rd", "city": "Bristol", "postcode": "BS1 1AA"},
        )
        assert s.address.city == "Bristol"

    def test_raises_if_profile_already_exists(self, pending_supplier, supplier_user):
        with pytest.raises(ValueError, match="already exists"):
            create_supplier_profile(user=supplier_user, business_name="Duplicate")


@pytest.mark.django_db
class TestUpdateSupplierProfile:
    def test_updates_description(self, pending_supplier):
        updated = update_supplier_profile(pending_supplier, description="Updated description")
        assert updated.description == "Updated description"

    def test_updates_address(self, pending_supplier):
        update_supplier_profile(
            pending_supplier,
            address_data={"line1": "New Street", "city": "Manchester", "postcode": "M1 1AA"},
        )
        pending_supplier.address.refresh_from_db()
        assert pending_supplier.address.city == "Manchester"

    def test_updates_shipping_policy(self, pending_supplier):
        from decimal import Decimal

        from apps.suppliers.models import ShippingPolicy

        updated = update_supplier_profile(
            pending_supplier,
            shipping_policy=ShippingPolicy.FREE_OVER_THRESHOLD,
            shipping_flat_rate=Decimal("3.50"),
            free_shipping_threshold=Decimal("40.00"),
        )
        assert updated.shipping_policy == ShippingPolicy.FREE_OVER_THRESHOLD
        assert updated.shipping_flat_rate == Decimal("3.50")
        assert updated.free_shipping_threshold == Decimal("40.00")

    def test_commission_rate_not_self_updatable(self, pending_supplier):
        # commission_rate is not in the allowed set, so profile updates must not change it.
        from decimal import Decimal

        original = pending_supplier.commission_rate
        updated = update_supplier_profile(pending_supplier, commission_rate=Decimal("1.00"))
        assert updated.commission_rate == original


@pytest.mark.django_db
class TestSupplierStatusActions:
    def test_approve_supplier(self, pending_supplier, admin_user):
        s = approve_supplier(pending_supplier, admin_user)
        assert s.status == SupplierStatus.APPROVED

    def test_suspend_supplier(self, approved_supplier, admin_user):
        s = suspend_supplier(approved_supplier, admin_user)
        assert s.status == SupplierStatus.SUSPENDED

    def test_reject_supplier(self, pending_supplier, admin_user):
        s = reject_supplier(pending_supplier, admin_user)
        assert s.status == SupplierStatus.REJECTED

    def test_set_commission_rate(self, pending_supplier):
        from decimal import Decimal

        s = set_commission_rate(pending_supplier, Decimal("15.00"))
        assert s.commission_rate == Decimal("15.00")


@pytest.mark.django_db
class TestDocumentServices:
    def test_upload_document_creates_pending_record(self, pending_supplier):
        doc = upload_document(
            supplier=pending_supplier,
            document_type=DocumentType.IDENTITY,
            file_url="https://example.com/passport.pdf",
        )
        assert doc.status == DocumentStatus.PENDING
        assert doc.supplier == pending_supplier

    def test_review_document_approve(self, pending_supplier, admin_user):
        doc = upload_document(
            pending_supplier, DocumentType.IDENTITY, "https://example.com/doc.pdf"
        )
        reviewed = review_document(doc, admin_user, approved=True, notes="Looks good")
        assert reviewed.status == DocumentStatus.APPROVED
        assert reviewed.reviewed_by == admin_user
        assert reviewed.reviewed_at is not None
        assert reviewed.notes == "Looks good"

    def test_review_document_reject(self, pending_supplier, admin_user):
        doc = upload_document(
            pending_supplier, DocumentType.IDENTITY, "https://example.com/doc.pdf"
        )
        reviewed = review_document(doc, admin_user, approved=False, notes="Document unclear")
        assert reviewed.status == DocumentStatus.REJECTED
