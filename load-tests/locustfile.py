"""
Provena load tests.

Run against a local server:
    locust -f locustfile.py --headless -u 50 -r 5 -t 60s --host http://localhost:8000

Run with web UI:
    locust -f locustfile.py --host http://localhost:8000
"""
import random
import string

from locust import HttpUser, SequentialTaskSet, between, task


def _random_email() -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"loadtest_{suffix}@example.com"


class BrowseCatalogueTaskSet(SequentialTaskSet):
    """Anonymous user browsing the catalogue."""

    @task
    def list_products(self):
        self.client.get("/api/v1/catalogue/products/", name="/catalogue/products")

    @task
    def list_products_filtered(self):
        self.client.get(
            "/api/v1/catalogue/products/?search=organic",
            name="/catalogue/products?search",
        )

    @task
    def list_categories(self):
        self.client.get("/api/v1/catalogue/categories/", name="/catalogue/categories")

    @task
    def view_product_detail(self):
        # Fetch a page to get real slugs
        res = self.client.get(
            "/api/v1/catalogue/products/",
            name="/catalogue/products (prefetch)",
        )
        if res.status_code == 200:
            results = res.json().get("results", [])
            if results:
                slug = random.choice(results)["slug"]
                self.client.get(
                    f"/api/v1/catalogue/products/{slug}/",
                    name="/catalogue/products/:slug",
                )


class BuyerCheckoutTaskSet(SequentialTaskSet):
    """Authenticated buyer: browse, add to cart, checkout."""

    token: str = ""
    product_variant_id: str = ""

    def on_start(self):
        email = _random_email()
        password = "TestPass1!"

        # Register
        self.client.post(
            "/api/v1/auth/register/",
            json={
                "email": email,
                "password": password,
                "first_name": "Load",
                "last_name": "Test",
                "role": "BUYER",
            },
            name="/auth/register",
        )

        # Login
        res = self.client.post(
            "/api/v1/auth/login/",
            json={"email": email, "password": password},
            name="/auth/login",
        )
        if res.status_code == 200:
            self.token = res.json().get("access", "")

        # Grab a real variant
        prod_res = self.client.get("/api/v1/catalogue/products/", name="/catalogue/products (setup)")
        if prod_res.status_code == 200:
            results = prod_res.json().get("results", [])
            for product in results:
                active_variants = [v for v in product.get("variants", []) if v.get("is_active")]
                if active_variants:
                    self.product_variant_id = active_variants[0]["id"]
                    break

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task
    def view_profile(self):
        self.client.get("/api/v1/auth/me/", headers=self._auth_headers(), name="/auth/me")

    @task
    def add_to_cart(self):
        if not self.product_variant_id:
            return
        self.client.post(
            "/api/v1/marketplace/cart/items/",
            json={"variant": self.product_variant_id, "quantity": 1},
            headers=self._auth_headers(),
            name="/cart/items (add)",
        )

    @task
    def view_cart(self):
        self.client.get(
            "/api/v1/marketplace/cart/",
            headers=self._auth_headers(),
            name="/cart",
        )

    @task
    def list_orders(self):
        self.client.get(
            "/api/v1/orders/",
            headers=self._auth_headers(),
            name="/orders",
        )


class AnonymousUser(HttpUser):
    wait_time = between(1, 3)
    weight = 7
    tasks = [BrowseCatalogueTaskSet]


class AuthenticatedBuyer(HttpUser):
    wait_time = between(2, 5)
    weight = 3
    tasks = [BuyerCheckoutTaskSet]
