#!/usr/bin/env bash
# post-check.sh for new-plugin-scaffold
# Runs lint and test suite after the scaffold is created.
set -euo pipefail

failed=0

if command -v pytest >/dev/null 2>&1; then
  pytest -q || failed=1
fi

if command -v ruff >/dev/null 2>&1; then
  ruff check . || failed=1
fi

if command -v markdownlint-cli2 >/dev/null 2>&1; then
  markdownlint-cli2 "**/*.md" || failed=1
fi

if [ "$failed" -ne 0 ]; then
  echo "post-check FAIL: at least one check failed." >&2
  exit 1
fi

echo "post-check OK"
exit 0
