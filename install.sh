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
for subdir in skills/aigovops plugins/aigovops persona \
              memory/aigovclaw/audit-log \
              memory/aigovclaw/risk-register memory/aigovclaw/soa \
              memory/aigovclaw/aisia memory/aigovclaw/nonconformity \
              memory/aigovclaw/role-matrix memory/aigovclaw/management-review \
              memory/aigovclaw/metrics memory/aigovclaw/gap-assessment \
              memory/aigovclaw/thresholds memory/aigovclaw/flagged-issues
do
  run mkdir -p "\"${WORKSPACE}/${subdir}\""
done

# Step 3: install the AIGovOps catalogue (skills + plugins).
#
# The skills catalogue lives in the aigovops repo. This repo (aigovclaw)
# contains only a README pointer under skills/. Sourcing order:
#   1. An adjacent aigovops checkout at ../aigovops (fast, offline-friendly).
#   2. Otherwise, clone aigovops from AIGOVOPS_REPO_URL.
echo "[3/5] Installing AIGovOps catalogue (skills and plugins)"

ADJACENT_AIGOVOPS="${REPO_ROOT}/../aigovops"
AIGOVOPS_ROOT=""

if [[ -d "${ADJACENT_AIGOVOPS}/skills" && -d "${ADJACENT_AIGOVOPS}/plugins" ]]; then
  AIGOVOPS_ROOT="${ADJACENT_AIGOVOPS}"
  echo "      Using adjacent aigovops checkout at ${AIGOVOPS_ROOT}"
else
  echo "      Cloning aigovops from ${AIGOVOPS_REPO_URL}"
  TMP_CLONE="$(mktemp -d)"
  run git clone --depth 1 "${AIGOVOPS_REPO_URL}" "\"${TMP_CLONE}/aigovops\""
  AIGOVOPS_ROOT="${TMP_CLONE}/aigovops"
fi

run rsync -a --delete \
  "\"${AIGOVOPS_ROOT}/skills/\"" \
  "\"${WORKSPACE}/skills/aigovops/\""
echo "      Skills deployed to ${WORKSPACE}/skills/aigovops/"

run rsync -a --delete \
  "\"${AIGOVOPS_ROOT}/plugins/\"" \
  "\"${WORKSPACE}/plugins/aigovops/\""
echo "      Plugins deployed to ${WORKSPACE}/plugins/aigovops/"

# Copy the AIGovClaw tool registration module into the workspace. This
# is Hermes-specific and lives in aigovclaw (not aigovops). Using
# rsync instead of cp -r so re-runs refresh cleanly.
run mkdir -p "\"${WORKSPACE}/tools\""
run rsync -a --delete "\"${REPO_ROOT}/tools/\"" "\"${WORKSPACE}/tools/\""
echo "      Tool registration module deployed to ${WORKSPACE}/tools/"

# Clean up the clone if we made one.
if [[ -n "${TMP_CLONE:-}" ]]; then
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

# Smoke tests on filesystem state.
if [[ "${DRY_RUN}" == "0" ]]; then
  SKILL_TEST="${WORKSPACE}/skills/aigovops/iso42001/SKILL.md"
  PLUGIN_TEST="${WORKSPACE}/plugins/aigovops/audit-log-generator/plugin.py"
  TOOLS_TEST="${WORKSPACE}/tools/registry.py"

  for path in "${SKILL_TEST}" "${PLUGIN_TEST}" "${TOOLS_TEST}"; do
    if [[ -f "${path}" ]]; then
      echo "      OK: ${path}"
    else
      echo "      MISSING: ${path}"
      exit 3
    fi
  done

  # Tool-registry smoke test: register all 9 AIGovOps plugins as Hermes
  # tools and verify the registry reports them read-only.
  if command -v python3 >/dev/null 2>&1; then
    echo "      Running tool-registry smoke test..."
    PYTHONPATH="${WORKSPACE}" python3 - <<PYEOF
import sys
sys.path.insert(0, "${WORKSPACE}")
from tools.aigovops_tools import register_aigovops_tools, unregister_all
from tools.registry import REGISTRY
unregister_all()
names = register_aigovops_tools("${WORKSPACE}/plugins/aigovops")
assert len(names) == 9, f"expected 9 tools, got {len(names)}"
for n in names:
    desc = REGISTRY.describe(n)
    assert desc["safety"]["is_read_only"] is True
print(f"      Tool registry: {len(names)} tools registered, all read-only")
PYEOF
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
