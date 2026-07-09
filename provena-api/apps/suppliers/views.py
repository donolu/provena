from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.audit import audit_action
from apps.accounts.permissions import IsAdmin
from apps.pagination import PaginatedListMixin

from . import services
from .models import Supplier, SupplierDocument, SupplierStatus
from .permissions import IsAnySupplier
from .serializers import (
    AdminSupplierSerializer,
    DocumentReviewSerializer,
    SupplierDocumentSerializer,
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

    @extend_schema(
        tags=["Suppliers (Public)"],
        summary="List approved suppliers",
        description="Returns all suppliers with APPROVED status. No authentication required.",
        responses={200: SupplierPublicSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        qs = Supplier.objects.filter(status=SupplierStatus.APPROVED).select_related("address")
        return Response(SupplierPublicSerializer(qs, many=True).data)


class SupplierRegistrationView(APIView):
    """Create a supplier profile for the authenticated user."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Suppliers (Supplier)"],
        summary="Register as a supplier",
        description="Creates a supplier profile for the authenticated user and upgrades their role "
        "to SUPPLIER. Profiles start in PENDING status pending admin KYC review. "
        "Each user may only have one supplier profile.",
        request=SupplierRegistrationSerializer,
        responses={
            201: SupplierProfileSerializer,
            400: OpenApiResponse(description="Validation error or profile already exists"),
        },
    )
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
            user=request.user,  # type: ignore[arg-type]
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

    @extend_schema(
        tags=["Suppliers (Supplier)"],
        summary="Get own supplier profile",
        responses={200: SupplierProfileSerializer},
    )
    def get(self, request: Request) -> Response:
        return Response(SupplierProfileSerializer(request.user.supplier).data)  # type: ignore[union-attr]

    @extend_schema(
        tags=["Suppliers (Supplier)"],
        summary="Update own supplier profile",
        description="Partial update. Address is nested; pass `null` to remove it. "
        "Status and commission rate cannot be self-updated.",
        request=SupplierProfileSerializer,
        responses={
            200: SupplierProfileSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def patch(self, request: Request) -> Response:
        s = SupplierProfileSerializer(request.user.supplier, data=request.data, partial=True)  # type: ignore[union-attr]
        s.is_valid(raise_exception=True)
        d = s.validated_data
        supplier = services.update_supplier_profile(
            request.user.supplier,  # type: ignore[union-attr]
            address_data=d.pop("address", None),
            **d,
        )
        return Response(SupplierProfileSerializer(supplier).data)


class SupplierPublicDetailView(APIView):
    """Public supplier profile by slug."""

    def get_permissions(self):
        return [AllowAny()]

    @extend_schema(
        tags=["Suppliers (Public)"],
        summary="Get approved supplier by slug",
        description="Returns the public profile for a single approved supplier. "
        "Returns 404 if the supplier is not found or not yet approved.",
        responses={
            200: SupplierPublicSerializer,
            404: OpenApiResponse(description="Not found or not approved"),
        },
    )
    def get(self, request: Request, slug: str) -> Response:
        supplier = get_object_or_404(Supplier, slug=slug, status=SupplierStatus.APPROVED)
        return Response(SupplierPublicSerializer(supplier).data)


class SupplierDocumentListView(APIView):
    """Supplier uploads KYC documents."""

    permission_classes = [IsAnySupplier]

    @extend_schema(
        tags=["Suppliers (Supplier)"],
        summary="List own KYC documents",
        responses={200: SupplierDocumentSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        docs = request.user.supplier.documents.all()  # type: ignore[union-attr]
        return Response(SupplierDocumentSerializer(docs, many=True).data)

    @extend_schema(
        tags=["Suppliers (Supplier)"],
        summary="Upload a KYC document",
        description="Registers a document by URL. The file itself must be uploaded directly to S3 "
        "via a presigned URL first; pass the resulting S3 URL here. "
        "Uploaded documents start in PENDING status for admin review.",
        request=UploadDocumentSerializer,
        responses={
            201: SupplierDocumentSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def post(self, request: Request) -> Response:
        s = UploadDocumentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        doc = services.upload_document(
            supplier=request.user.supplier,  # type: ignore[union-attr]
            document_type=d["document_type"],
            file_url=d["file_url"],
        )
        return Response(SupplierDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


class SupplierPerformanceView(APIView):
    """Supplier performance stats."""

    permission_classes = [IsAnySupplier]

    @extend_schema(
        tags=["Suppliers (Supplier)"],
        summary="Get own performance stats",
        description="Returns order volume, revenue, average rating, and fulfilment rate. "
        "Currently returns zeroes until the orders and payments apps are built.",
        responses={200: OpenApiResponse(description="Performance stats object")},
    )
    def get(self, request: Request) -> Response:
        return Response(services.get_performance_stats(request.user.supplier))  # type: ignore[union-attr]


class StripeConnectView(APIView):
    """Return the Stripe Connect onboarding URL for the supplier."""

    permission_classes = [IsAnySupplier]

    @extend_schema(
        tags=["Stripe Connect"],
        summary="Get Stripe Connect onboarding URL",
        description="Creates or resumes a Stripe Connect Express onboarding session. "
        "Redirect the supplier to the returned `onboarding_url`. "
        "Once onboarding is complete, Stripe redirects back to the supplier profile.",
        responses={
            200: OpenApiResponse(
                description="`{onboarding_url: 'https://connect.stripe.com/...'}`"
            ),
            503: OpenApiResponse(description="Stripe Connect is not configured on this server"),
        },
    )
    def get(self, request: Request) -> Response:
        from django.conf import settings as django_settings

        frontend_url = getattr(django_settings, "FRONTEND_URL", "http://localhost:3000")
        return_url = f"{frontend_url}/supplier/payouts/?connected=1"
        refresh_url = request.build_absolute_uri("/api/v1/suppliers/me/stripe-connect/")
        url = services.get_stripe_connect_onboarding_url(
            request.user.supplier,  # type: ignore[union-attr]
            return_url=return_url,
            refresh_url=refresh_url,
        )
        if not url:
            return Response(
                {"detail": "Payment features are not configured on this server."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"onboarding_url": url})


# Admin views


class AdminSupplierListView(PaginatedListMixin, APIView):
    """Admin: list all suppliers with optional status filter."""

    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin: Suppliers"],
        summary="List all suppliers",
        description="Returns all suppliers. Filter by `?status=PENDING|APPROVED|SUSPENDED|REJECTED`.",
        parameters=[
            OpenApiParameter(
                name="status",
                description="Filter by supplier status",
                required=False,
                enum=["PENDING", "APPROVED", "SUSPENDED", "REJECTED"],
            )
        ],
        responses={200: AdminSupplierSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        qs = Supplier.objects.select_related("user", "address").prefetch_related("documents")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        return self.paginate(qs, AdminSupplierSerializer, request)


class AdminSupplierDetailView(APIView):
    """Admin: view and update a supplier (commission rate, etc.)."""

    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin: Suppliers"],
        summary="Get supplier detail",
        responses={
            200: AdminSupplierSerializer,
            404: OpenApiResponse(description="Not found"),
        },
    )
    def get(self, request: Request, pk: str) -> Response:
        supplier = get_object_or_404(Supplier, pk=pk)
        return Response(AdminSupplierSerializer(supplier).data)

    @extend_schema(
        tags=["Admin: Suppliers"],
        summary="Update supplier (admin)",
        description="Allows updating the commission rate and other admin-only fields.",
        request=AdminSupplierSerializer,
        responses={
            200: AdminSupplierSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Not found"),
        },
    )
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

    @extend_schema(
        tags=["Admin: Suppliers"],
        summary="Approve supplier",
        description="Transitions the supplier from PENDING (or SUSPENDED) to APPROVED. "
        "Triggers a notification email to the supplier.",
        request=None,
        responses={
            200: OpenApiResponse(description="`{status: 'APPROVED'}`"),
            404: OpenApiResponse(description="Not found"),
        },
    )
    @audit_action(
        "supplier.approved", target_type="Supplier", get_target_id=lambda req, kw: kw.get("pk")
    )
    def post(self, request: Request, pk: str) -> Response:
        supplier = get_object_or_404(Supplier, pk=pk)
        services.approve_supplier(supplier, request.user)  # type: ignore[arg-type]
        return Response({"status": supplier.status})


class AdminSupplierSuspendView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin: Suppliers"],
        summary="Suspend supplier",
        description="Suspends an approved supplier. Pass an optional `reason` in the request body.",
        request=SupplierStatusActionSerializer,
        responses={
            200: OpenApiResponse(description="`{status: 'SUSPENDED'}`"),
            404: OpenApiResponse(description="Not found"),
        },
    )
    @audit_action(
        "supplier.suspended", target_type="Supplier", get_target_id=lambda req, kw: kw.get("pk")
    )
    def post(self, request: Request, pk: str) -> Response:
        supplier = get_object_or_404(Supplier, pk=pk)
        s = SupplierStatusActionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.suspend_supplier(supplier, request.user)  # type: ignore[arg-type]
        return Response({"status": supplier.status})


class AdminSupplierRejectView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin: Suppliers"],
        summary="Reject supplier",
        description="Rejects a PENDING supplier application. Pass an optional `reason` in the request body.",
        request=SupplierStatusActionSerializer,
        responses={
            200: OpenApiResponse(description="`{status: 'REJECTED'}`"),
            404: OpenApiResponse(description="Not found"),
        },
    )
    @audit_action(
        "supplier.rejected", target_type="Supplier", get_target_id=lambda req, kw: kw.get("pk")
    )
    def post(self, request: Request, pk: str) -> Response:
        supplier = get_object_or_404(Supplier, pk=pk)
        s = SupplierStatusActionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.reject_supplier(supplier, request.user)  # type: ignore[arg-type]
        return Response({"status": supplier.status})


class AdminDocumentListView(APIView):
    """Admin: list all documents, filtered to pending by default."""

    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin: KYC Documents"],
        summary="List KYC documents",
        description="Returns documents across all suppliers. Defaults to `?status=PENDING`. "
        "Pass `?status=APPROVED` or `?status=REJECTED` to see reviewed documents.",
        parameters=[
            OpenApiParameter(
                name="status",
                description="Filter by document status (default: PENDING)",
                required=False,
                enum=["PENDING", "APPROVED", "REJECTED"],
            )
        ],
        responses={200: SupplierDocumentSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        status_filter = request.query_params.get("status", "PENDING").upper()
        qs = SupplierDocument.objects.select_related("supplier", "reviewed_by")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(SupplierDocumentSerializer(qs, many=True).data)


class AdminDocumentReviewView(APIView):
    """Admin: approve or reject a KYC document."""

    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin: KYC Documents"],
        summary="Review a KYC document",
        description="Approves or rejects a single document. "
        "Set `approved: true` or `approved: false`. "
        "Optional `notes` field for rejection reasons shown to the supplier.",
        request=DocumentReviewSerializer,
        responses={
            200: SupplierDocumentSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Not found"),
        },
    )
    def post(self, request: Request, pk: str) -> Response:
        document = get_object_or_404(SupplierDocument, pk=pk)
        s = DocumentReviewSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        doc = services.review_document(
            document=document,
            admin_user=request.user,  # type: ignore[arg-type]
            approved=s.validated_data["approved"],
            notes=s.validated_data.get("notes", ""),
        )
        return Response(SupplierDocumentSerializer(doc).data)
