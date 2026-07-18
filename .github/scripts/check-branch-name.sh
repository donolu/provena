#!/usr/bin/env bash
# Validates the current branch name against the project naming convention.
# Runs as a pre-push hook via pre-commit (stages: [pre-push]).
# Skipped on main itself (direct pushes to main are prevented by branch protection).

set -euo pipefail

BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || true)

# Skip the check on main and any detached HEAD state (e.g. CI checkout)
if [[ "$BRANCH" == "main" || -z "$BRANCH" ]]; then
  exit 0
fi

PATTERN='^(feature|fix|chore|docs|ci)/[0-9]+-[a-z][a-z0-9-]*$'

if [[ ! "$BRANCH" =~ $PATTERN ]]; then
  echo ""
  echo "  Branch name '$BRANCH' does not match the required convention."
  echo ""
  echo "  Required format:  <type>/<issue-number>-<short-description>"
  echo ""
  echo "  Examples:"
  echo "    feature/42-add-search"
  echo "    fix/17-cart-reservation-race"
  echo "    chore/88-bump-ruff"
  echo "    docs/5-deployment-guide"
  echo "    ci/91-add-trivy-scan"
  echo ""
  echo "  Allowed types: feature, fix, chore, docs, ci"
  echo "  The issue number must come from a GitHub Issue."
  echo ""
  exit 1
fi

exit 0
