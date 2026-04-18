#!/usr/bin/env bash
# post-check.sh for dep-bump
# Runs test and lint suite after dependency bump. Exit non-zero means do not open PR.
set -euo pipefail

failed=0

if command -v pytest >/dev/null 2>&1; then
  pytest -q || failed=1
fi

if command -v ruff >/dev/null 2>&1; then
  ruff check . || failed=1
fi

if [ -f "package.json" ] && command -v npm >/dev/null 2>&1; then
  if npm run --silent 2>/dev/null | grep -q "^  test"; then
    npm test --silent || failed=1
  fi
  if npm run --silent 2>/dev/null | grep -q "^  lint"; then
    npm run lint --silent || failed=1
  fi
fi

if [ "$failed" -ne 0 ]; then
  echo "post-check FAIL: at least one test or lint job failed." >&2
  exit 1
fi

echo "post-check OK"
exit 0
