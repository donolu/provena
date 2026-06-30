from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin

from . import services
from .models import Supplier, SupplierDocument, SupplierStatus
from .permissions import IsAnySupplier
from .serializers import (
    AdminSupplierSerializer,
    DocumentReviewSerializer,
    SupplierProfileSerializer,
    SupplierPublicSerializer,
    SupplierRegistrationSerializer,
    SupplierStatusActionSerializer,
    UploadDocumentSerializer,
)


class SupplierListView(APIView):
    """Public list of approved suppliers."""

    def get_permissions(self):
        return [AllowAny()]

    def get(self, request: Request) -> Response:
        qs = Supplier.objects.filter(status=SupplierStatus.APPROVED).select_related("address")
        return Response(SupplierPublicSerializer(qs, many=True).data)


class SupplierRegistrationView(APIView):
    """Create a supplier profile for the authenticated user."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        if hasattr(request.user, "supplier"):
            return Response(
                {
                    "error": {
                        "code": "ALREADY_EXISTS",
                        "message": "You already have a supplier profile.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        s = SupplierRegistrationSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        supplier = services.create_supplier_profile(
            user=request.user,
            business_name=d["business_name"],
            description=d.get("description", ""),
            phone=d.get("phone", ""),
            website=d.get("website", ""),
            logo_url=d.get("logo_url", ""),
            address_data=d.get("address"),
        )
        return Response(SupplierProfileSerializer(supplier).data, status=status.HTTP_201_CREATED)


class SupplierProfileView(APIView):
    """Supplier views and updates their own profile."""

    permission_classes = [IsAnySupplier]

    def get(self, request: Request) -> Response:
        return Response(SupplierProfileSerializer(request.user.supplier).data)

    def patch(self, request: Request) -> Response:
        s = SupplierProfileSerializer(request.user.supplier, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        supplier = services.update_supplier_profile(
            request.user.supplier,
            address_data=d.pop("address", None),
            **d,
        )
        return Response(SupplierProfileSerializer(supplier).data)


class SupplierPublicDetailView(APIView):
    """Public supplier profile by slug."""

    def get_permissions(self):
        return [AllowAny()]

    def get(self, request: Request, slug: str) -> Response:
        supplier = get_object_or_404(Supplier, slug=slug, status=SupplierStatus.APPROVED)
        return Response(SupplierPublicSerializer(supplier).data)


class SupplierDocumentListView(APIView):
    """Supplier uploads KYC documents."""

    permission_classes = [IsAnySupplier]

    def get(self, request: Request) -> Response:
        docs = request.user.supplier.documents.all()
        from .serializers import SupplierDocumentSerializer

        return Response(SupplierDocumentSerializer(docs, many=True).data)

    def post(self, request: Request) -> Response:
        s = UploadDocumentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        doc = services.upload_document(
            supplier=request.user.supplier,
            document_type=d["document_type"],
            file_url=d["file_url"],
        )
        from .serializers import SupplierDocumentSerializer

        return Response(SupplierDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


class SupplierPerformanceView(APIView):
    """Supplier performance stats."""

    permission_classes = [IsAnySupplier]

    def get(self, request: Request) -> Response:
        return Response(services.get_performance_stats(request.user.supplier))


class StripeConnectView(APIView):
    """Return the Stripe Connect onboarding URL for the supplier."""

    permission_classes = [IsAnySupplier]

    def get(self, request: Request) -> Response:
        return_url = f"{request.build_absolute_uri('/api/v1/suppliers/me/')}"
        refresh_url = f"{request.build_absolute_uri('/api/v1/suppliers/me/stripe-connect/')}"
        url = services.get_stripe_connect_onboarding_url(
            request.user.supplier, return_url=return_url, refresh_url=refresh_url
        )
        return Response({"onboarding_url": url})


# Admin views


class AdminSupplierListView(APIView):
    """Admin: list all suppliers with optional status filter."""

    permission_classes = [IsAdmin]

    def get(self, request: Request) -> Response:
        qs = Supplier.objects.select_related("user", "address").prefetch_related("documents")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        return Response(AdminSupplierSerializer(qs, many=True).data)


class AdminSupplierDetailView(APIView):
    """Admin: view and update a supplier (commission rate, etc.)."""

    permission_classes = [IsAdmin]

    def get(self, request: Request, pk: str) -> Response:
        supplier = get_object_or_404(Supplier, pk=pk)
        return Response(AdminSupplierSerializer(supplier).data)

    def patch(self, request: Request, pk: str) -> Response:
        supplier = get_object_or_404(Supplier, pk=pk)
        s = AdminSupplierSerializer(supplier, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        if "commission_rate" in d:
            services.set_commission_rate(supplier, d["commission_rate"])
        return Response(AdminSupplierSerializer(supplier).data)


class AdminSupplierApproveView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request: Request, pk: str) -> Response:
        supplier = get_object_or_404(Supplier, pk=pk)
        services.approve_supplier(supplier, request.user)
        return Response({"status": supplier.status})


class AdminSupplierSuspendView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request: Request, pk: str) -> Response:
        supplier = get_object_or_404(Supplier, pk=pk)
        s = SupplierStatusActionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.suspend_supplier(supplier, request.user)
        return Response({"status": supplier.status})


class AdminSupplierRejectView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request: Request, pk: str) -> Response:
        supplier = get_object_or_404(Supplier, pk=pk)
        s = SupplierStatusActionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.reject_supplier(supplier, request.user)
        return Response({"status": supplier.status})


class AdminDocumentListView(APIView):
    """Admin: list all documents, filtered to pending by default."""

    permission_classes = [IsAdmin]

    def get(self, request: Request) -> Response:
        from .serializers import SupplierDocumentSerializer

        status_filter = request.query_params.get("status", "PENDING").upper()
        qs = SupplierDocument.objects.select_related("supplier", "reviewed_by")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(SupplierDocumentSerializer(qs, many=True).data)


class AdminDocumentReviewView(APIView):
    """Admin: approve or reject a KYC document."""

    permission_classes = [IsAdmin]

    def post(self, request: Request, pk: str) -> Response:
        document = get_object_or_404(SupplierDocument, pk=pk)
        s = DocumentReviewSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        doc = services.review_document(
            document=document,
            admin_user=request.user,
            approved=s.validated_data["approved"],
            notes=s.validated_data.get("notes", ""),
        )
        from .serializers import SupplierDocumentSerializer

        return Response(SupplierDocumentSerializer(doc).data)
