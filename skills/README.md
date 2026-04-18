# skills/

This directory holds the AIGovOps skills catalogue used by the AIGovClaw agent at runtime.

## Source

The contents of this directory are sourced from [aigovops/aigovops](https://github.com/ZOLAtheCodeX/aigovops). Do not edit skill files in place here. Edit them upstream and re-sync.

The installer (`install.sh`) populates this directory at install time. Re-running `./install.sh` updates the skills to match the current upstream catalogue.

## Why skills are pulled, not vendored

Vendoring skill content into this repository would create two divergent copies of every SKILL.md and force coordinated changes across two repositories for every skill update. Pulling at install time keeps a single source of truth (the AIGovOps catalogue) and keeps this repository focused on runtime configuration.

## Layout after install

```text
skills/
├── iso42001/
│   └── SKILL.md
├── nist-ai-rmf/
│   └── SKILL.md
└── ... (additional skills as the upstream catalogue grows)
```

## What the agent does with these skills

At runtime, Hermes Agent reads each SKILL.md as knowledge context. The agent uses the skills to ground its outputs in the authoritative framework material. Skills are not executable code; they are knowledge artifacts.

For executable governance artifacts (audit logs, risk register entries, gap assessments), see the workflows in `../workflows/`. Workflows invoke plugins from the AIGovOps catalogue.

## Pinning to a specific catalogue version

Phase 3. The current installer pulls the latest upstream `main`. A future installer release will support pinning to a specific catalogue release tag.
