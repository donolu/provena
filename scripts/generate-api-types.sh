#!/usr/bin/env bash
# Exports the OpenAPI schema from Django and regenerates TypeScript types.
# Run from the repo root after any serializer or URL changes.
#
# Usage: ./scripts/generate-api-types.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_DIR="$REPO_ROOT/provena-api"
WEB_DIR="$REPO_ROOT/provena-web"

VENV=""
for candidate in "$API_DIR/.venv312" "$API_DIR/.venv" "$API_DIR/venv"; do
  if [ -f "$candidate/bin/python" ] && "$candidate/bin/python" -c "import django" 2>/dev/null; then
    VENV="$candidate"
    break
  fi
done

if [ -z "$VENV" ]; then
  echo "Error: no Python 3.12 virtual env with Django found in provena-api. Create one with:" >&2
  echo "  PYENV_VERSION=3.12.13 pyenv exec python -m venv provena-api/.venv312" >&2
  echo "  provena-api/.venv312/bin/pip install -e 'provena-api[dev]'" >&2
  exit 1
fi

export DJANGO_SETTINGS_MODULE=config.settings.development
export DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-local-schema-key}"
export DATABASE_URL="${DATABASE_URL:-sqlite:////tmp/schema_gen.db}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export STRIPE_SECRET_KEY="${STRIPE_SECRET_KEY:-sk_test_placeholder}"
export STRIPE_PUBLISHABLE_KEY="${STRIPE_PUBLISHABLE_KEY:-pk_test_placeholder}"
export STRIPE_WEBHOOK_SECRET="${STRIPE_WEBHOOK_SECRET:-whsec_placeholder}"

echo "Exporting OpenAPI schema..."
cd "$API_DIR"
"$VENV/bin/python" manage.py spectacular --file "$WEB_DIR/schema.yaml"

echo "Generating TypeScript types..."
cd "$WEB_DIR"
npm run generate:types

echo "Done. Commit provena-web/src/lib/api/generated/ if changed."
