#!/usr/bin/env bash
# post-check.sh for citation-drift
# Greps changed files for STYLE.md-noncompliant citation patterns.
# Exit 0 means no drift remains; exit 1 names offending file and line.
set -euo pipefail

failed=0

# Bad pattern: 'ISO/IEC 42001' lacking ':2023' year suffix, followed by Clause/Annex.
# Mirrors tests/audit/consistency_audit.py:audit_citation_format.
if [ "$#" -eq 0 ]; then
  # Scan all .md files under the current directory.
  targets=$(find . -type f -name '*.md' -not -path './.git/*')
else
  targets="$*"
fi

for f in $targets; do
  [ -f "$f" ] || continue
  # grep -P for Perl regex (lookahead). Fall back to egrep if -P unavailable.
  if grep -nP 'ISO/IEC 42001(?!:2023)\s*,\s*(Clause|Annex A)' "$f" >/dev/null 2>&1; then
    grep -nP 'ISO/IEC 42001(?!:2023)\s*,\s*(Clause|Annex A)' "$f"
    failed=1
  fi
done

if [ "$failed" -ne 0 ]; then
  echo "post-check FAIL: ISO citation missing ':2023' year suffix. See resources/citation-rules.md." >&2
  exit 1
fi

echo "post-check OK: citations match STYLE.md."
exit 0
