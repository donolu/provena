import pyotp
import pytest

from apps.accounts.models import Address, User

URL = "/api/v1/auth/me/delete/"


@pytest.mark.django_db
class TestAccountDeletion:
    def test_buyer_erases_account(self, buyer_client, buyer):
        Address.objects.create(
            user=buyer, full_name="Test Buyer", line1="1 Street", city="London", postcode="EC1A 1BB"
        )
        res = buyer_client.post(URL, {"password": "Securepass123!"})
        assert res.status_code == 204

        buyer.refresh_from_db()
        assert buyer.email == f"deleted-{buyer.id}@deleted.invalid"
        assert buyer.first_name == "" and buyer.last_name == ""
        assert buyer.is_active is False
        assert buyer.erased_at is not None
        assert not buyer.has_usable_password()
        assert Address.objects.filter(user=buyer).count() == 0

    def test_wrong_password_is_rejected_and_account_untouched(self, buyer_client, buyer):
        res = buyer_client.post(URL, {"password": "not-my-password"})
        assert res.status_code == 400
        buyer.refresh_from_db()
        assert buyer.is_active is True
        assert buyer.erased_at is None

    def test_supplier_cannot_self_erase(self, api_client, supplier):
        api_client.force_authenticate(user=supplier)
        res = api_client.post(URL, {"password": "Securepass123!"})
        assert res.status_code == 403
        supplier.refresh_from_db()
        assert supplier.is_active is True

    def test_totp_required_when_enabled(self, buyer_client, buyer):
        secret = pyotp.random_base32()
        buyer.totp_enabled = True
        buyer.totp_secret = secret
        buyer.save(update_fields=["totp_enabled", "totp_secret"])

        # Missing/invalid code is rejected.
        assert buyer_client.post(URL, {"password": "Securepass123!"}).status_code == 400
        buyer.refresh_from_db()
        assert buyer.is_active is True

        # Valid code completes erasure.
        code = pyotp.TOTP(secret).now()
        res = buyer_client.post(URL, {"password": "Securepass123!", "totp_code": code})
        assert res.status_code == 204
        buyer.refresh_from_db()
        assert buyer.is_active is False and buyer.totp_enabled is False

    def test_erased_email_is_freed_for_reuse(self, buyer_client, buyer):
        original = buyer.email
        buyer_client.post(URL, {"password": "Securepass123!"})
        # The address is anonymised, so a new account can take the old email.
        assert not User.objects.filter(email=original).exists()
