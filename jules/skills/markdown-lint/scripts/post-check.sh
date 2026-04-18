#!/usr/bin/env bash
# post-check.sh for markdown-lint
# Runs markdownlint-cli2 (or markdownlint) against changed files.
set -euo pipefail

if command -v markdownlint-cli2 >/dev/null 2>&1; then
  markdownlint-cli2 "**/*.md"
  exit $?
fi

if command -v markdownlint >/dev/null 2>&1; then
  markdownlint "**/*.md"
  exit $?
fi

echo "post-check: neither markdownlint-cli2 nor markdownlint installed." >&2
exit 1
