import pytest

from apps.suppliers.models import (
    DocumentStatus,
    DocumentType,
    SupplierDocument,
    SupplierStatus,
)


@pytest.mark.django_db
class TestSupplierModel:
    def test_str_returns_business_name(self, pending_supplier):
        assert str(pending_supplier) == "Fresh Farms Ltd"

    def test_is_approved_false_when_pending(self, pending_supplier):
        assert pending_supplier.is_approved is False

    def test_is_approved_true_when_approved(self, approved_supplier):
        assert approved_supplier.is_approved is True

    def test_uuid_primary_key(self, pending_supplier):
        assert len(str(pending_supplier.pk)) == 36

    def test_default_status_is_pending(self, pending_supplier):
        assert pending_supplier.status == SupplierStatus.PENDING

    def test_default_commission_rate(self, pending_supplier):
        assert float(pending_supplier.commission_rate) == 10.0


@pytest.mark.django_db
class TestUniqueSlug:
    def test_slug_generated_from_business_name(self, pending_supplier):
        assert pending_supplier.slug == "fresh-farms-ltd"

    def test_slug_suffixed_on_collision(self, pending_supplier, supplier_user):
        from apps.accounts.models import Role, User

        user2 = User.objects.create_user(
            email="vendor2@example.com", password="Securepass123!", role=Role.SUPPLIER
        )
        from apps.suppliers.services import create_supplier_profile

        supplier2 = create_supplier_profile(user=user2, business_name="Fresh Farms Ltd")
        assert supplier2.slug == "fresh-farms-ltd-1"


@pytest.mark.django_db
class TestSupplierAddress:
    def test_address_linked_to_supplier(self, pending_supplier):
        assert pending_supplier.address.city == "London"
        assert pending_supplier.address.postcode == "E1 1AA"

    def test_str_includes_city_and_postcode(self, pending_supplier):
        assert "London" in str(pending_supplier.address)
        assert "E1 1AA" in str(pending_supplier.address)


@pytest.mark.django_db
class TestSupplierDocument:
    def test_document_created_with_pending_status(self, pending_supplier):
        doc = SupplierDocument.objects.create(
            supplier=pending_supplier,
            document_type=DocumentType.IDENTITY,
            file_url="https://example.com/doc.pdf",
        )
        assert doc.status == DocumentStatus.PENDING
        assert doc.reviewed_at is None
        assert doc.reviewed_by is None

    def test_str_includes_supplier_name(self, pending_supplier):
        doc = SupplierDocument.objects.create(
            supplier=pending_supplier,
            document_type=DocumentType.FOOD_HYGIENE,
            file_url="https://example.com/cert.pdf",
        )
        assert "Fresh Farms Ltd" in str(doc)
