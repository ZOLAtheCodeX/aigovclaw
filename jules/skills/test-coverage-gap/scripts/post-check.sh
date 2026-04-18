#!/usr/bin/env bash
# post-check.sh for test-coverage-gap
# Runs the repo test suite. Exit non-zero means do not open the PR.
set -euo pipefail

if command -v pytest >/dev/null 2>&1; then
  pytest -q
  exit $?
fi

if [ -f "package.json" ]; then
  npm test --silent
  exit $?
fi

echo "post-check: no recognized test runner (pytest or npm). Skipping." >&2
exit 0
