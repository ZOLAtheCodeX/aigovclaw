#!/usr/bin/env bash
set -euo pipefail

# AIGovClaw Installer
#
# Installs the AIGovClaw configuration into a Hermes Agent workspace:
# copies the AIGovOps skills catalogue, installs the governance persona,
# applies security-scoped Hermes runtime configuration, and verifies the
# install.
#
# Usage:
#   ./install.sh [--dry-run] [--skip-hermes-check] [--workspace PATH]
#
# Flags:
#   --dry-run             Print actions without modifying any files.
#   --skip-hermes-check   Install AIGovClaw files without verifying that
#                         Hermes Agent is present. Use in CI or when
#                         preparing an image that will have Hermes added
#                         later.
#   --workspace PATH      Install into the specified workspace instead of
#                         the default ~/.hermes.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_WORKSPACE="${HOME}/.hermes"
WORKSPACE="${DEFAULT_WORKSPACE}"
DRY_RUN=0
SKIP_HERMES_CHECK=0
AIGOVOPS_REPO_URL="${AIGOVOPS_REPO_URL:-https://github.com/ZOLAtheCodeX/aigovops}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --skip-hermes-check) SKIP_HERMES_CHECK=1 ;;
    --workspace)
      shift
      WORKSPACE="$1"
      ;;
    -h|--help)
      sed -n '1,30p' "${BASH_SOURCE[0]}" | sed 's/^# //; s/^#//'
      exit 0
      ;;
    *)
      echo "Unknown flag: $1" >&2
      exit 2
      ;;
  esac
  shift
done

run() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    echo "[dry-run] $*"
  else
    eval "$@"
  fi
}

echo "=== AIGovClaw Installer ==="
echo "Repo root:       ${REPO_ROOT}"
echo "Workspace:       ${WORKSPACE}"
echo "Dry-run:         $([ "${DRY_RUN}" == 1 ] && echo yes || echo no)"
echo "Skip hermes chk: $([ "${SKIP_HERMES_CHECK}" == 1 ] && echo yes || echo no)"
echo

# Step 1: verify Hermes Agent availability unless skipped.
if [[ "${SKIP_HERMES_CHECK}" == "0" ]]; then
  if command -v hermes >/dev/null 2>&1; then
    echo "[1/5] Hermes Agent detected: $(command -v hermes)"
  else
    echo "[1/5] Hermes Agent not found on PATH."
    cat <<'MSG'

AIGovClaw requires Hermes Agent. Install it first following the
upstream instructions at https://github.com/NousResearch/hermes-agent
and re-run this installer.

If you intend to install AIGovClaw files without Hermes present (for
example while preparing an image), re-run with --skip-hermes-check.

MSG
    exit 1
  fi
fi

# Step 2: prepare workspace layout.
echo "[2/5] Preparing workspace at ${WORKSPACE}"
for subdir in skills/aigovops persona memory/aigovclaw/audit-log \
              memory/aigovclaw/risk-register memory/aigovclaw/soa \
              memory/aigovclaw/aisia memory/aigovclaw/nonconformity \
              memory/aigovclaw/role-matrix memory/aigovclaw/management-review \
              memory/aigovclaw/metrics memory/aigovclaw/gap-assessment \
              memory/aigovclaw/thresholds memory/aigovclaw/flagged-issues
do
  run mkdir -p "\"${WORKSPACE}/${subdir}\""
done

# Step 3: copy or sync the AIGovOps skills catalogue.
echo "[3/5] Syncing AIGovOps skills catalogue to ${WORKSPACE}/skills/aigovops/"
SKILLS_SOURCE="${REPO_ROOT}/skills"
if [[ -d "${SKILLS_SOURCE}" && -n "$(ls -A "${SKILLS_SOURCE}" 2>/dev/null || true)" ]]; then
  run rsync -a --delete \
    "\"${SKILLS_SOURCE}/\"" \
    "\"${WORKSPACE}/skills/aigovops/\""
else
  echo "      Local skills/ directory empty; pulling from ${AIGOVOPS_REPO_URL}"
  TMP_CLONE="$(mktemp -d)"
  run git clone --depth 1 "${AIGOVOPS_REPO_URL}" "\"${TMP_CLONE}\""
  run rsync -a --delete \
    "\"${TMP_CLONE}/skills/\"" \
    "\"${WORKSPACE}/skills/aigovops/\""
  run rm -rf "\"${TMP_CLONE}\""
fi

# Step 4: install persona and runtime config.
echo "[4/5] Installing persona and Hermes configuration"
run cp "\"${REPO_ROOT}/persona/SOUL.md\"" "\"${WORKSPACE}/SOUL.md\""
# Preserve an existing config if present; AIGovClaw writes to a dedicated
# file so it does not overwrite arbitrary user config.
run cp "\"${REPO_ROOT}/config/hermes.yaml\"" "\"${WORKSPACE}/config.aigovclaw.yaml\""
echo "      Persona written to ${WORKSPACE}/SOUL.md"
echo "      Config written to ${WORKSPACE}/config.aigovclaw.yaml"
echo "      Merge into your primary config.yaml per config/hermes.yaml comments."

# Step 5: verify.
echo "[5/5] Verifying installation"
if [[ "${SKIP_HERMES_CHECK}" == "0" ]] && command -v hermes >/dev/null 2>&1; then
  if [[ "${DRY_RUN}" == "1" ]]; then
    echo "[dry-run] hermes doctor"
  else
    if hermes doctor 2>/dev/null; then
      echo "      hermes doctor: OK"
    else
      echo "      hermes doctor returned non-zero. Review output above."
    fi
  fi
else
  echo "      Hermes check skipped."
fi

# Smoke-test: confirm a skill is readable at the expected path.
if [[ "${DRY_RUN}" == "0" ]]; then
  SKILL_TEST="${WORKSPACE}/skills/aigovops/iso42001/SKILL.md"
  if [[ -f "${SKILL_TEST}" ]]; then
    echo "      iso42001 SKILL.md present: OK"
  else
    echo "      iso42001 SKILL.md missing at ${SKILL_TEST}. Investigate."
    exit 3
  fi
fi

echo
echo "AIGovClaw setup complete."
echo
cat <<'NEXT_STEPS'
Next steps:
  1. Select your LLM provider:    hermes model
  2. Start the agent:              hermes
  3. Review the agent persona:     $WORKSPACE/SOUL.md
  4. Review the config:            $WORKSPACE/config.aigovclaw.yaml
  5. First governance workflow:    run the audit-log workflow to
                                    generate an entry against your
                                    first AI system inventory item.

For the full workflow catalogue see workflows/ in this repository.
For plugin documentation see https://github.com/ZOLAtheCodeX/aigovops.
NEXT_STEPS
