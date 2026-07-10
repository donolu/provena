import pytest


@pytest.mark.django_db
class TestMetricsEndpoint:
    def test_exposes_prometheus_text_format(self, client):
        res = client.get("/metrics")
        assert res.status_code == 200
        assert res["Content-Type"].startswith("text/plain")
        body = res.content.decode()
        # prometheus_client always exports process/python metrics
        assert "python_info" in body
        # django-prometheus HTTP instrumentation
        assert "django_http_requests_total_by_method" in body

    def test_records_request_metrics(self, client):
        # Generate a request the middleware will count, then read metrics.
        client.get("/api/v1/health/")
        body = client.get("/metrics").content.decode()
        assert "django_http_responses_total_by_status" in body

    def test_metrics_and_health_exempt_from_ssl_redirect(self, client, settings):
        # Production enforces HTTPS; internal scrape/probe paths must be exempt
        # so Prometheus and health checks over plain HTTP are not 301'd.
        settings.SECURE_SSL_REDIRECT = True
        settings.SECURE_REDIRECT_EXEMPT = [r"^metrics$", r"^api/v1/health/$"]
        assert client.get("/metrics").status_code == 200
        assert client.get("/api/v1/health/").status_code == 200
        # A normal path is still redirected to HTTPS.
        assert client.get("/api/v1/catalogue/products/").status_code == 301
