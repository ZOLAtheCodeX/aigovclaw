#!/usr/bin/env bash
# stale-check.sh
# Shared Step 0 stale-issue gate used by every Jules maintenance skill.
#
# Verifies that every marker string named in the FlaggedIssue payload still
# exists at the current HEAD of the target branch. If any marker is absent,
# exits 1 and names the missing marker. The calling skill must then return
# verdict "rejected-stale" and not open a PR.
#
# Usage:
#   stale-check.sh <issue-title> <target-file> <marker> [<target-file> <marker> ...]
#
# Argument pairs are file/marker. Each marker must appear at least once in
# the named file.
#
# Exit codes:
#   0  all markers present
#   1  at least one marker absent (message names the missing marker)
#   2  usage error
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "usage: stale-check.sh <issue-title> <target-file> <marker> [<target-file> <marker> ...]" >&2
  exit 2
fi

issue_title="$1"
shift

if [ $(( $# % 2 )) -ne 0 ]; then
  echo "error: file/marker arguments must come in pairs" >&2
  exit 2
fi

missing=0
while [ "$#" -gt 0 ]; do
  file="$1"
  marker="$2"
  shift 2

  if [ ! -f "$file" ]; then
    echo "MISSING: file not found: $file (issue: $issue_title)" >&2
    missing=1
    continue
  fi

  if ! grep -nF -- "$marker" "$file" >/dev/null; then
    echo "MISSING: marker absent in $file: $marker (issue: $issue_title)" >&2
    missing=1
  else
    grep -nF -- "$marker" "$file" | head -n 1
  fi
done

if [ "$missing" -ne 0 ]; then
  echo "stale-check FAIL: at least one marker absent at HEAD. Return verdict rejected-stale." >&2
  exit 1
fi

echo "stale-check OK: all markers present at HEAD"
exit 0
