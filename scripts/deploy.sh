#!/usr/bin/env bash
#
# Zero-downtime rolling deploy for the Docker Compose stack (#15 / ADR-010 stack).
#
#   scripts/deploy.sh [service ...]     # default: api web
#   TARGET_REPLICAS=3 scripts/deploy.sh api
#
# For each service it builds the new image, starts TARGET_REPLICAS new replicas
# alongside the running ones, waits until they report healthy, then retires the
# old replicas. Nginx (Docker-DNS resolution + proxy_next_upstream in
# nginx/nginx.conf) keeps serving from the healthy replicas throughout, so there
# is no downtime window.
#
# IMPORTANT: run database migrations FIRST, and keep them backward compatible
# (expand/contract) — old and new code run simultaneously during the roll.
# Migrations use the direct connection, not PgBouncer:
#   docker compose exec api sh -c \
#     'DATABASE_URL="$DIRECT_DATABASE_URL" python manage.py migrate --no-input'
#
# Respects COMPOSE_FILE / -f via the standard `docker compose` resolution.

set -euo pipefail

TARGET_REPLICAS="${TARGET_REPLICAS:-2}"
if [ "$#" -gt 0 ]; then SERVICES=("$@"); else SERVICES=(api web); fi

wait_healthy() {
    svc="$1"; want="$2"; tries=60; i=1
    while [ "$i" -le "$tries" ]; do
        healthy=0
        for id in $(docker compose ps -q "$svc"); do
            # Services with a healthcheck report starting/healthy/unhealthy; count
            # only "healthy". Services without one have no health status, so fall
            # back to the container's running state (best effort — no readiness
            # signal to gate on).
            status=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$id" 2>/dev/null || echo gone)
            case "$status" in
                healthy | running) healthy=$((healthy + 1)) ;;
            esac
        done
        printf '\r     %s: %s/%s healthy   ' "$svc" "$healthy" "$want"
        if [ "$healthy" -ge "$want" ]; then printf '\n'; return 0; fi
        sleep 3; i=$((i + 1))
    done
    printf '\n'; echo "ERROR: $svc did not reach $want healthy replicas in time" >&2; return 1
}

echo "==> Building images: ${SERVICES[*]}"
docker compose build "${SERVICES[@]}"

for svc in "${SERVICES[@]}"; do
    echo "==> Rolling '$svc' to $TARGET_REPLICAS new replica(s)"
    old=$(docker compose ps -q "$svc" || true)
    n=$(printf '%s\n' "$old" | grep -c . || true)
    total=$((n + TARGET_REPLICAS))

    echo "   starting $TARGET_REPLICAS new replica(s) alongside $n old"
    docker compose up -d --no-deps --no-recreate --scale "$svc=$total" "$svc"

    wait_healthy "$svc" "$total"

    if [ "$n" -gt 0 ]; then
        echo "   retiring $n old replica(s)"
        # shellcheck disable=SC2086
        docker stop $old >/dev/null
        # shellcheck disable=SC2086
        docker rm $old >/dev/null
    fi
    echo "   '$svc' now serving from $TARGET_REPLICAS new replica(s)"
done

echo "==> Deploy complete (zero downtime)"
