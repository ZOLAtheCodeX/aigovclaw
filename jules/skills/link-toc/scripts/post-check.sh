#!/usr/bin/env bash
# post-check.sh for link-toc
# Runs a link checker over README and referenced files.
set -euo pipefail

if command -v markdown-link-check >/dev/null 2>&1; then
  for f in "$@"; do
    markdown-link-check -q "$f"
  done
  exit $?
fi

if command -v lychee >/dev/null 2>&1; then
  lychee "$@"
  exit $?
fi

echo "post-check: no link checker installed (markdown-link-check or lychee)." >&2
exit 1
