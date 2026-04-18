#!/usr/bin/env bash
# post-check.sh for prohibited-content-sweep
# Greps the modified files for em-dashes, non-ASCII in .md, and hedging
# phrases from resources/prohibited-content.md. Exit 0 means clean.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
resources="${script_dir}/../resources/prohibited-content.md"

if [ "$#" -eq 0 ]; then
  targets=$(find . -type f \( -name '*.md' -o -name '*.py' \) -not -path './.git/*')
else
  targets="$*"
fi

failed=0

for f in $targets; do
  [ -f "$f" ] || continue

  # Em-dash U+2014.
  if grep -nP '\x{2014}' "$f" >/dev/null 2>&1; then
    grep -nP '\x{2014}' "$f" | sed "s|^|$f: em-dash: |"
    failed=1
  fi

  # Non-ASCII in .md files.
  case "$f" in
    *.md)
      if LC_ALL=C grep -nP '[^\x00-\x7F]' "$f" >/dev/null 2>&1; then
        LC_ALL=C grep -nP '[^\x00-\x7F]' "$f" | sed "s|^|$f: non-ascii: |"
        failed=1
      fi
      ;;
  esac

  # Hedging phrases.
  for phrase in "may want to consider" "might be helpful to" "could potentially" "it is possible that" "you might find" "we suggest you might"; do
    if grep -niF -- "$phrase" "$f" >/dev/null 2>&1; then
      grep -niF -- "$phrase" "$f" | sed "s|^|$f: hedging: |"
      failed=1
    fi
  done
done

if [ "$failed" -ne 0 ]; then
  echo "post-check FAIL: prohibited content present. See ${resources}." >&2
  exit 1
fi

echo "post-check OK: no prohibited content."
exit 0
