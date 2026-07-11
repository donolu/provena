#!/usr/bin/env bash
#
# One-command local Provena stack — the whole thing, end to end.
#
#   scripts/up.sh          Build + start every service, migrate, seed demo data,
#                          and index the catalogue for search. Then open
#                          http://localhost.
#   scripts/up.sh --monitoring   ...also start the observability stack
#                          (Prometheus + Grafana + exporters).
#   scripts/up.sh down     Stop and remove the stack (keeps your data).
#   scripts/up.sh reset    Stop and remove the stack AND its data volumes.
#   scripts/up.sh logs     Tail logs for all services.
#
# Uses the development overrides: dev settings, hot reload, no real secrets
# required. Search (Typesense) and the Celery worker/beat all run too, so this
# is a faithful end-to-end environment.

set -euo pipefail

cd "$(dirname "$0")/.."

# Parse a --monitoring / -m flag out of the args; the remainder is the command.
WITH_MONITORING=0
CMD=""
for arg in "$@"; do
    case "$arg" in
        --monitoring | -m) WITH_MONITORING=1 ;;
        *) [ -z "$CMD" ] && CMD="$arg" ;;
    esac
done
CMD="${CMD:-up}"

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.dev.yml)
# Include the monitoring compose when the flag is set (always for teardown, so
# it cleans up whether or not it was started with monitoring).
if [ "$WITH_MONITORING" = 1 ] || [ "$CMD" = down ] || [ "$CMD" = reset ]; then
    COMPOSE+=(-f docker-compose.monitoring.yml)
fi

case "$CMD" in
    down)
        "${COMPOSE[@]}" down
        exit 0
        ;;
    reset)
        "${COMPOSE[@]}" down -v
        exit 0
        ;;
    logs)
        "${COMPOSE[@]}" logs -f
        exit 0
        ;;
    up) ;;
    *)
        echo "usage: scripts/up.sh [up|down|reset|logs] [--monitoring]" >&2
        exit 2
        ;;
esac

wait_for() {
    name="$1"
    url="$2"
    printf '==> Waiting for %s' "$name"
    for _ in $(seq 1 90); do
        if curl -sf "$url" >/dev/null 2>&1; then
            printf ' ready\n'
            return 0
        fi
        printf '.'
        sleep 2
    done
    printf '\n'
    echo "ERROR: $name did not come up in time." >&2
    "${COMPOSE[@]}" logs --tail 30 api
    exit 1
}

echo "==> Building and starting all services (first run pulls images and builds; give it a few minutes)"
"${COMPOSE[@]}" up -d --build

# /api/v1/health/ checks the database too, so a 200 through Nginx means the API
# and DB are both ready.
wait_for "the API" "http://localhost/api/v1/health/"

echo "==> Applying database migrations (direct connection, bypassing PgBouncer)"
# shellcheck disable=SC2016  # $DIRECT_DATABASE_URL must expand inside the container, not here
"${COMPOSE[@]}" exec -T api sh -c \
    'DATABASE_URL="$DIRECT_DATABASE_URL" python manage.py migrate --no-input'

echo "==> Seeding demo data (idempotent)"
"${COMPOSE[@]}" exec -T api python manage.py seed_e2e_data >/dev/null

printf '==> Waiting for Typesense'
for _ in $(seq 1 30); do
    if curl -sf "http://localhost:8108/health" >/dev/null 2>&1; then
        ts_ready=1
        break
    fi
    printf '.'
    sleep 2
done
printf '\n'
if [ "${ts_ready:-}" = 1 ]; then
    echo "==> Indexing the catalogue for search"
    "${COMPOSE[@]}" exec -T api python manage.py reindex_search || true
else
    echo "==> Typesense not ready; search will use the Postgres fallback"
fi

cat <<'EOF'

============================================================
  Provena is up.   Open  ->  http://localhost
============================================================
  Demo logins (password: E2ePassw0rd!)
    buyer     e2e-buyer@provena.test
    supplier  e2e-supplier@provena.test   2FA secret below
    admin     e2e-admin@provena.test      2FA secret below

  Supplier 2FA secret:  JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP
  Admin    2FA secret:  KRSXG5CTMVRXEZLUKRSXG5CTMVRXEZLU
  (add the secret to any authenticator app to get the 6-digit code)

  URLs
    App           http://localhost
    API           http://localhost:8000/api/v1/
    API docs      http://localhost:8000/api/v1/schema/swagger-ui/
    Typesense     http://localhost:8108

  Manage
    Tail logs     scripts/up.sh logs
    Stop          scripts/up.sh down
    Wipe data     scripts/up.sh reset

  The web app compiles on first load (dev mode), so the first page may take
  a few seconds.
============================================================
EOF

if [ "$WITH_MONITORING" = 1 ]; then
    cat <<'EOF'
  Observability
    Grafana       http://localhost:3001   (admin / admin)
    Prometheus    http://localhost:9090
    API metrics   http://localhost:8000/metrics
============================================================
EOF
fi
