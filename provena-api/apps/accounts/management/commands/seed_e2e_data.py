"""Seed deterministic data for the Playwright end-to-end suite.

Creates a buyer, an approved supplier, an admin, and a pending supplier, plus a
minimal active catalogue with stock. Idempotent: safe to run repeatedly against
the same database.

The TOTP-protected roles (supplier, admin) are seeded with fixed base32 secrets
so the E2E login helper can generate valid codes and complete two-factor login.
These secrets are test-only and are echoed to stdout for the workflow to pass to
Playwright as E2E_SUPPLIER_TOTP_SECRET / E2E_ADMIN_TOTP_SECRET.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

# Fixed, test-only TOTP secrets (valid base32). Not used outside E2E.
SUPPLIER_TOTP_SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"  # noqa: S105  # nosec B105
ADMIN_TOTP_SECRET = "KRSXG5CTMVRXEZLUKRSXG5CTMVRXEZLU"  # noqa: S105  # nosec B105


class Command(BaseCommand):
    help = "Seed deterministic data for the Playwright E2E suite (idempotent)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--password", default="E2ePassw0rd!")
        parser.add_argument("--buyer-email", default="e2e-buyer@provena.test")
        parser.add_argument("--supplier-email", default="e2e-supplier@provena.test")
        parser.add_argument("--admin-email", default="e2e-admin@provena.test")
        parser.add_argument("--pending-supplier-email", default="e2e-pending@provena.test")

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        from apps.catalogue.models import Category, Product, ProductStatus, ProductVariant
        from apps.inventory.models import StockLevel
        from apps.suppliers.models import Supplier, SupplierAddress, SupplierStatus

        password = options["password"]

        # ── Buyer (no TOTP) ──────────────────────────────────────────────────
        self._upsert_user(
            options["buyer_email"], password, role="BUYER", first_name="E2E", last_name="Buyer"
        )

        # ── Admin (TOTP enforced) ────────────────────────────────────────────
        self._upsert_user(
            options["admin_email"],
            password,
            role="ADMIN",
            first_name="E2E",
            last_name="Admin",
            is_staff=True,
            is_superuser=True,
            totp_secret=ADMIN_TOTP_SECRET,
            totp_enabled=True,
        )

        # ── Approved supplier (TOTP enforced) ────────────────────────────────
        supplier_user = self._upsert_user(
            options["supplier_email"],
            password,
            role="SUPPLIER",
            first_name="E2E",
            last_name="Supplier",
            totp_secret=SUPPLIER_TOTP_SECRET,
            totp_enabled=True,
        )
        supplier, _ = Supplier.objects.update_or_create(
            user=supplier_user,
            defaults={
                "business_name": "E2E Test Supplier",
                "slug": "e2e-test-supplier",
                "description": "Deterministic supplier for end-to-end tests.",
                "status": SupplierStatus.APPROVED,
            },
        )
        SupplierAddress.objects.update_or_create(
            supplier=supplier,
            defaults={
                "line1": "1 Test Street",
                "city": "London",
                "postcode": "EC1A 1BB",
                "country": "GB",
            },
        )

        # ── Pending supplier (for the admin approval journey) ────────────────
        pending_user = self._upsert_user(
            options["pending_supplier_email"],
            password,
            role="SUPPLIER",
            first_name="E2E",
            last_name="Pending",
        )
        Supplier.objects.update_or_create(
            user=pending_user,
            defaults={
                "business_name": "E2E Pending Supplier",
                "slug": "e2e-pending-supplier",
                "description": "Awaiting approval; used by the admin approval test.",
                "status": SupplierStatus.PENDING,
            },
        )

        # ── Minimal active catalogue with stock ──────────────────────────────
        category, _ = Category.objects.update_or_create(
            slug="e2e-test-category",
            defaults={"name": "E2E Test Category", "is_active": True},
        )
        product, _ = Product.objects.update_or_create(
            slug="e2e-test-product",
            defaults={
                "supplier": supplier,
                "category": category,
                "name": "E2E Test Product",
                "description": "A deterministic product for end-to-end tests.",
                "status": ProductStatus.ACTIVE,
            },
        )
        variant, _ = ProductVariant.objects.update_or_create(
            sku="E2E-SKU-001",
            defaults={
                "product": product,
                "name": "Default",
                "price": Decimal("9.99"),
                "is_active": True,
            },
        )
        StockLevel.objects.update_or_create(
            variant=variant,
            defaults={"quantity_available": 100, "quantity_reserved": 0},
        )

        self.stdout.write(self.style.SUCCESS("E2E data seeded."))
        self.stdout.write(f"E2E_BUYER_EMAIL={options['buyer_email']}")
        self.stdout.write(f"E2E_SUPPLIER_EMAIL={options['supplier_email']}")
        self.stdout.write(f"E2E_ADMIN_EMAIL={options['admin_email']}")
        self.stdout.write(f"E2E_SUPPLIER_TOTP_SECRET={SUPPLIER_TOTP_SECRET}")
        self.stdout.write(f"E2E_ADMIN_TOTP_SECRET={ADMIN_TOTP_SECRET}")

    def _upsert_user(self, email: str, password: str, **fields):
        """Create or update a user, always resetting the password and flags."""
        from apps.accounts.models import User

        email = email.lower()
        user = User.objects.filter(email=email).first()
        if user is None:
            user = User(email=email)
        for key, value in fields.items():
            setattr(user, key, value)
        user.set_password(password)
        user.save()
        return user
