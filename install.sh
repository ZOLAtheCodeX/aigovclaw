#!/usr/bin/env bash
set -euo pipefail

# AIGovClaw Installer
# Installs Hermes Agent and configures the AIGovClaw governance workspace.
# Usage: ./install.sh

echo "=== AIGovClaw Setup ==="

# Step 1: Check for Hermes Agent, install if missing
# TODO: detect existing Hermes installation; if missing run:
# TODO: curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# Step 2: Copy skills into Hermes workspace
# TODO: cp -r skills/ ~/.hermes/skills/aigovops/

# Step 3: Set AIGovClaw persona
# TODO: cp persona/SOUL.md ~/.hermes/SOUL.md

# Step 4: Apply security-scoped Hermes config
# TODO: cp config/hermes.yaml ~/.hermes/config.yaml

# Step 5: Verify installation
# TODO: hermes doctor

echo "AIGovClaw setup complete."
echo "Run 'hermes model' to select your LLM provider."
echo "Run 'hermes' to start your AI governance operations agent."
