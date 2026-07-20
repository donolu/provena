"""Return-policy resolution: category default, product override, and the perishable-safe
fallback when a product has no category (ADR-014)."""

import pytest

from apps.catalogue.models import Category, Product, ReturnPolicy


@pytest.mark.django_db
class TestEffectiveReturnPolicy:
    def _product(self, approved_supplier, category=None, override=""):
        return Product.objects.create(
            supplier=approved_supplier,
            category=category,
            name="Item",
            slug=f"item-{override or (category.slug if category else 'none')}",
            return_policy_override=override,
        )

    def test_new_category_defaults_to_defective_only(self, db):
        cat = Category.objects.create(name="Berries", slug="berries")
        assert cat.return_policy == ReturnPolicy.DEFECTIVE_ONLY

    def test_inherits_category_default(self, approved_supplier):
        cat = Category.objects.create(name="Perishable", slug="perishable")
        p = self._product(approved_supplier, category=cat)
        assert p.effective_return_policy == ReturnPolicy.DEFECTIVE_ONLY

    def test_inherits_returnable_category(self, approved_supplier):
        cat = Category.objects.create(
            name="Pantry", slug="pantry", return_policy=ReturnPolicy.RETURNABLE
        )
        p = self._product(approved_supplier, category=cat)
        assert p.effective_return_policy == ReturnPolicy.RETURNABLE

    def test_product_override_wins(self, approved_supplier):
        cat = Category.objects.create(
            name="Pantry2", slug="pantry2", return_policy=ReturnPolicy.RETURNABLE
        )
        p = self._product(approved_supplier, category=cat, override=ReturnPolicy.DEFECTIVE_ONLY)
        assert p.effective_return_policy == ReturnPolicy.DEFECTIVE_ONLY

    def test_no_category_falls_back_to_defective_only(self, approved_supplier):
        p = self._product(approved_supplier, category=None)
        assert p.effective_return_policy == ReturnPolicy.DEFECTIVE_ONLY

    def test_sealed_category_resolves(self, approved_supplier):
        cat = Category.objects.create(
            name="Hygiene", slug="hygiene", return_policy=ReturnPolicy.SEALED
        )
        p = self._product(approved_supplier, category=cat)
        assert p.effective_return_policy == ReturnPolicy.SEALED
