#!/usr/bin/env bash
# install.sh
# Install all 8 Jules maintenance skills into a target agent's skills directory.
#
# Usage:
#   install.sh --target <agent> [--symlink] [--dry-run]
#
# Targets:
#   claude-code  -> ~/.claude/skills/<name>/
#   jules        -> `npx skills add` (per skill)
#   cursor       -> ~/.cursor/skills/<name>/
#   gemini-cli   -> ~/.gemini/skills/<name>/
#   antigravity  -> ~/.antigravity/skills/<name>/
#
# Flags:
#   --symlink  use ln -s instead of cp -R (fast iteration during development).
#   --dry-run  print actions without executing.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SKILLS=(
  "framework-drift"
  "test-coverage-gap"
  "dep-bump"
  "citation-drift"
  "markdown-lint"
  "new-plugin-scaffold"
  "link-toc"
  "prohibited-content-sweep"
)

target=""
use_symlink=0
dry_run=0

usage() {
  sed -n '2,20p' "$0"
  exit 2
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target)
      target="${2:-}"
      shift 2
      ;;
    --symlink)
      use_symlink=1
      shift
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage
      ;;
  esac
done

if [ -z "$target" ]; then
  echo "error: --target is required" >&2
  usage
fi

case "$target" in
  claude-code) dest_root="${HOME}/.claude/skills" ;;
  cursor)      dest_root="${HOME}/.cursor/skills" ;;
  gemini-cli)  dest_root="${HOME}/.gemini/skills" ;;
  antigravity) dest_root="${HOME}/.antigravity/skills" ;;
  jules)       dest_root="" ;;
  *)
    echo "error: unknown target: $target" >&2
    usage
    ;;
esac

run() {
  if [ "$dry_run" -eq 1 ]; then
    echo "[dry-run] $*"
  else
    eval "$@"
  fi
}

if [ "$target" = "jules" ]; then
  if ! command -v npx >/dev/null 2>&1; then
    echo "error: npx not found; required for --target jules" >&2
    exit 1
  fi
  for skill in "${SKILLS[@]}"; do
    run "npx skills add google-labs-code/jules-skills --skill ${skill} --global"
  done
  echo "installed ${#SKILLS[@]} skill(s) into jules registry."
  exit 0
fi

run "mkdir -p '${dest_root}'"

for skill in "${SKILLS[@]}"; do
  src="${SCRIPT_DIR}/${skill}"
  dst="${dest_root}/${skill}"
  if [ ! -d "$src" ]; then
    echo "warning: source missing: $src" >&2
    continue
  fi
  if [ -e "$dst" ]; then
    run "rm -rf '${dst}'"
  fi
  if [ "$use_symlink" -eq 1 ]; then
    run "ln -s '${src}' '${dst}'"
  else
    run "cp -R '${src}' '${dst}'"
  fi
done

echo "installed ${#SKILLS[@]} skill(s) into ${dest_root}"
