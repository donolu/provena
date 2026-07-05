#!/usr/bin/env bash
set -euo pipefail

# Prefer the project venv; fall back to whatever mypy is on PATH.
# Exits 0 (skip) if mypy is not installed anywhere, to avoid blocking
# developers who haven't set up the full dev environment yet.
MYPY_BIN=""
for candidate in "provena-api/.venv312/bin/mypy" "provena-api/venv/bin/mypy"; do
    if [[ -x "$candidate" ]]; then
        MYPY_BIN="$PWD/$candidate"
        break
    fi
done
if [[ -z "$MYPY_BIN" ]]; then
    if command -v mypy >/dev/null 2>&1; then
        MYPY_BIN="$(command -v mypy)"
    else
        echo "mypy not found; skipping type check locally (CI will verify)"
        echo "To set up: cd provena-api && pip install -e '.[dev]'"
        exit 0
    fi
fi

export DJANGO_SECRET_KEY=ci-mypy-check
export DJANGO_SETTINGS_MODULE=config.settings.development
export DATABASE_URL=postgres://localhost/mypy_check
export REDIS_URL=redis://localhost/0
export STRIPE_SECRET_KEY=sk_test_placeholder
export STRIPE_PUBLISHABLE_KEY=pk_test_placeholder
export STRIPE_WEBHOOK_SECRET=whsec_placeholder

cd provena-api && "$MYPY_BIN" apps/
