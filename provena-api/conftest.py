import threading

import pytest
from django.db import connection
from rest_framework.test import APIClient

from apps.accounts.models import Role, User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def requires_postgres():
    """Skip a test unless the DB is PostgreSQL (real row locking, not sqlite's serialisation)."""
    if connection.vendor != "postgresql":
        pytest.skip("Concurrency tests require PostgreSQL row locking")


@pytest.fixture
def run_concurrently():
    """Run ``target`` in ``n`` threads that all enter the critical section together.

    Each thread waits on a barrier before calling ``target`` (to maximise contention),
    captures its return value or exception, and closes its own DB connection afterwards.
    Returns a list of ``("ok", value)`` / ``("error", exc)`` tuples, one per thread.
    Use with ``@pytest.mark.django_db(transaction=True)`` so the threads see committed rows.
    """

    def _run(target, n: int = 2):
        barrier = threading.Barrier(n)
        results: list = [None] * n

        def worker(i: int) -> None:
            try:
                barrier.wait()
                results[i] = ("ok", target())
            except Exception as exc:
                results[i] = ("error", exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return results

    return _run


@pytest.fixture
def buyer(db):
    return User.objects.create_user(
        email="buyer@example.com",
        password="Securepass123!",  # noqa: S106  # nosec B106
        first_name="Test",
        last_name="Buyer",
        role=Role.BUYER,
    )


@pytest.fixture
def supplier(db):
    return User.objects.create_user(
        email="supplier@example.com",
        password="Securepass123!",  # noqa: S106  # nosec B106
        first_name="Test",
        last_name="Supplier",
        role=Role.SUPPLIER,
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@example.com",
        password="Securepass123!",  # noqa: S106  # nosec B106
        first_name="Test",
        last_name="Admin",
        role=Role.ADMIN,
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def buyer_client(api_client, buyer):
    api_client.force_authenticate(user=buyer)
    return api_client


@pytest.fixture
def supplier_client(api_client, supplier):
    api_client.force_authenticate(user=supplier)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client
