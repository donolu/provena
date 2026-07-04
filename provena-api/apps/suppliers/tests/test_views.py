import pytest
from rest_framework import status

REGISTER_URL = "/api/v1/suppliers/register/"
ME_URL = "/api/v1/suppliers/me/"
DOCUMENTS_URL = "/api/v1/suppliers/me/documents/"
PERFORMANCE_URL = "/api/v1/suppliers/me/performance/"
PUBLIC_LIST_URL = "/api/v1/suppliers/"
ADMIN_LIST_URL = "/api/v1/suppliers/admin/"
ADMIN_DOCS_URL = "/api/v1/suppliers/admin/documents/"


@pytest.mark.django_db
class TestSupplierRegistration:
    def test_authenticated_user_can_register(self, buyer_client):
        res = buyer_client.post(
            REGISTER_URL,
            {
                "business_name": "My Fresh Farm",
                "description": "Great produce",
                "phone": "07700900000",
            },
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["business_name"] == "My Fresh Farm"
        assert res.data["status"] == "PENDING"

    def test_unauthenticated_cannot_register(self, api_client):
        res = api_client.post(REGISTER_URL, {"business_name": "Test"})
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_duplicate_registration_returns_400(self, supplier_user_client, pending_supplier):
        res = supplier_user_client.post(REGISTER_URL, {"business_name": "Another Farm"})
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_business_name_returns_400(self, buyer_client):
        res = buyer_client.post(REGISTER_URL, {"description": "No name"})
        assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestSupplierProfileView:
    def test_supplier_can_view_own_profile(self, supplier_user_client, pending_supplier):
        res = supplier_user_client.get(ME_URL)
        assert res.status_code == status.HTTP_200_OK
        assert res.data["business_name"] == "Fresh Farms Ltd"
        assert res.data["status"] == "PENDING"

    def test_unauthenticated_cannot_access_profile(self, api_client):
        res = api_client.get(ME_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_supplier_can_update_description(self, supplier_user_client, pending_supplier):
        res = supplier_user_client.patch(ME_URL, {"description": "Now with organic options"})
        assert res.status_code == status.HTTP_200_OK
        assert res.data["description"] == "Now with organic options"

    def test_supplier_cannot_change_status(self, supplier_user_client, pending_supplier):
        res = supplier_user_client.patch(ME_URL, {"status": "APPROVED"})
        assert res.status_code == status.HTTP_200_OK
        assert res.data["status"] == "PENDING"


@pytest.mark.django_db
class TestPublicSupplierViews:
    def test_public_list_shows_only_approved(self, api_client, pending_supplier, approved_supplier):
        res = api_client.get(PUBLIC_LIST_URL)
        assert res.status_code == status.HTTP_200_OK
        names = [s["business_name"] for s in res.data]
        assert "Fresh Farms Ltd" in names
        assert len(res.data) == 1  # pending not shown

    def test_public_detail_by_slug(self, api_client, approved_supplier):
        res = api_client.get(f"/api/v1/suppliers/{approved_supplier.slug}/")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["slug"] == approved_supplier.slug

    def test_pending_supplier_not_in_public_detail(self, api_client, pending_supplier):
        res = api_client.get(f"/api/v1/suppliers/{pending_supplier.slug}/")
        assert res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestSupplierDocuments:
    def test_supplier_can_upload_document(self, supplier_user_client, pending_supplier):
        res = supplier_user_client.post(
            DOCUMENTS_URL,
            {
                "document_type": "IDENTITY",
                "file_url": "https://example.com/passport.pdf",
            },
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["status"] == "PENDING"

    def test_supplier_can_list_own_documents(self, supplier_user_client, pending_supplier):
        supplier_user_client.post(
            DOCUMENTS_URL,
            {
                "document_type": "IDENTITY",
                "file_url": "https://example.com/doc.pdf",
            },
        )
        res = supplier_user_client.get(DOCUMENTS_URL)
        assert res.status_code == status.HTTP_200_OK
        assert len(res.data) == 1

    def test_invalid_document_type_returns_400(self, supplier_user_client, pending_supplier):
        res = supplier_user_client.post(
            DOCUMENTS_URL,
            {
                "document_type": "INVALID_TYPE",
                "file_url": "https://example.com/doc.pdf",
            },
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestSupplierPerformance:
    def test_returns_stats_dict(self, supplier_user_client, pending_supplier):
        res = supplier_user_client.get(PERFORMANCE_URL)
        assert res.status_code == status.HTTP_200_OK
        assert "total_orders" in res.data
        assert "total_revenue" in res.data


@pytest.mark.django_db
class TestAdminSupplierViews:
    def test_admin_can_list_all_suppliers(self, admin_client, pending_supplier, approved_supplier):
        res = admin_client.get(ADMIN_LIST_URL)
        assert res.status_code == status.HTTP_200_OK
        assert len(res.data) == 1  # both pending and approved from the fixture

    def test_admin_can_filter_by_status(self, admin_client, pending_supplier):
        res = admin_client.get(f"{ADMIN_LIST_URL}?status=pending")
        assert res.status_code == status.HTTP_200_OK
        assert all(s["status"] == "PENDING" for s in res.data)

    def test_non_admin_cannot_access_admin_list(self, buyer_client):
        res = buyer_client.get(ADMIN_LIST_URL)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_approve_supplier(self, admin_client, pending_supplier):
        res = admin_client.post(f"/api/v1/suppliers/admin/{pending_supplier.pk}/approve/")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["status"] == "APPROVED"

    def test_admin_can_suspend_supplier(self, admin_client, approved_supplier):
        res = admin_client.post(f"/api/v1/suppliers/admin/{approved_supplier.pk}/suspend/")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["status"] == "SUSPENDED"

    def test_admin_can_reject_supplier(self, admin_client, pending_supplier):
        res = admin_client.post(f"/api/v1/suppliers/admin/{pending_supplier.pk}/reject/")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["status"] == "REJECTED"

    def test_admin_can_update_commission_rate(self, admin_client, pending_supplier):
        res = admin_client.patch(
            f"/api/v1/suppliers/admin/{pending_supplier.pk}/",
            {"commission_rate": "15.00"},
        )
        assert res.status_code == status.HTTP_200_OK

    def test_admin_can_review_document(self, admin_client, pending_supplier):
        from apps.suppliers.models import DocumentType
        from apps.suppliers.services import upload_document

        doc = upload_document(
            pending_supplier, DocumentType.IDENTITY, "https://example.com/doc.pdf"
        )
        res = admin_client.post(
            f"/api/v1/suppliers/admin/documents/{doc.pk}/review/",
            {"approved": True, "notes": "All clear"},
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.data["status"] == "APPROVED"
        assert res.data["notes"] == "All clear"

    def test_admin_can_list_pending_documents(self, admin_client, pending_supplier):
        from apps.suppliers.models import DocumentType
        from apps.suppliers.services import upload_document

        upload_document(pending_supplier, DocumentType.IDENTITY, "https://example.com/doc.pdf")
        res = admin_client.get(ADMIN_DOCS_URL)
        assert res.status_code == status.HTTP_200_OK
        assert len(res.data) == 1
