# Monitoring

Provena exposes Prometheus metrics for infrastructure observability, complementing Sentry (which handles error and performance tracing).

## What's exposed

- **Django** (`api:8000/metrics`, via `django-prometheus`): HTTP request rate, response status counts, request latency histograms, and database query metrics.
- **Celery** (`celery-exporter:9808`): task throughput, per-state counts, task runtime histograms, and queue length. The worker runs with `-E` and `CELERY_WORKER_SEND_TASK_EVENTS` / `CELERY_TASK_SEND_SENT_EVENT` enabled so the exporter can consume task events.
- **Redis** (`redis-exporter:9121`): broker metrics.

`/metrics` is mounted at the API root and is only reachable inside the Docker network (`api:8000/metrics`). Public traffic through Nginx never routes to it, so it is not exposed externally.

## Running the stack locally

```bash
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

- Prometheus: http://localhost:9090 (check **Status → Targets** — all should be `UP`)
- Grafana: http://localhost:3001 (default `admin` / `admin`; override with `GRAFANA_USER` / `GRAFANA_PASSWORD`)

Grafana is provisioned automatically with the Prometheus datasource and the **Provena Overview** dashboard (`monitoring/grafana/dashboards/provena-overview.json`), covering request rate, error rate, request latency, database queries, Celery task runtime, and queue depth.

## Production

Point an existing Prometheus at `api:8000/metrics`, `celery-exporter:9808`, and `redis-exporter:9121` (see `monitoring/prometheus.yml` for the scrape config). Restrict network access to these targets to the monitoring system.

Under multiple API worker processes, use `prometheus_client` multiprocess mode (`PROMETHEUS_MULTIPROC_DIR`); the default daphne single-process container per service needs no extra configuration.
