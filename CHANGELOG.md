# Changelog

All notable changes to AIGovClaw are recorded here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Stable public schemas are called out explicitly. Breaking changes to these schemas bump the minor version pre-1.0 and the major version post-1.0.

## [Unreleased]

### Added

- **Stable schemas at the ingress and audit boundaries.** Stdlib-only dataclasses. No third-party dependency required.
  - `aigovclaw.task_envelope.TaskEnvelope`: canonical form for external callers (Hub v2 HTTP API, CLI, channel adapters, scheduled triggers). Fields: `envelope_id`, `command`, `args`, `source_type`, `source_id`, `actor`, `rationale`, `requested_at`, `dry_run`, `metadata`. Nine validator tests.
  - `aigovclaw.action_executor.audit_event.AuditEvent`: canonical shape of audit log entries. Thirteen declared event types from `action-intent` through `workflow-completed` and `quality-gate-failed`. Lossless round-trip against the legacy flat writer via `from_dict` and `to_dict`. Seven tests.
  - `risk_tier` on every `ActionSpec`. Four tiers: `low`, `medium`, `high`, `critical`. Classification rule documented on the dataclass. Surfaced in `action-intent` audit entries and in the pending-approval list output.
- **Canonical end-to-end demos.** Each demo ships an input fixture, a stdlib-only runner that exercises `TaskEnvelope` plus the relevant aigovops plugin plus `AuditEvent` emission, a README, and a pytest replay test gated in CI.
  - [demos/audit-log/](demos/audit-log/): ISO/IEC 42001 audit log entry for a high-risk clinical-triage AI system at a regional health insurer. Ten Annex A controls mapped.
  - [demos/gap-assessment/](demos/gap-assessment/): full ISO/IEC 42001 Annex A sweep against a two-system AIMS at Contoso Health Insurance. Thirty-eight controls classified across covered, partially-covered, not-covered, not-applicable with a coverage score of 15.3 percent.
  - [demos/README.md](demos/README.md): index and the shared four-file convention.
- **Memory model documentation.** [docs/memory-model.md](docs/memory-model.md) codifies four memory classes (A operational, B workflow, C skill-pattern, D protected-governance) with their directory roots, writer rules, reader rules, and promotion rules. Grounded against the paths the runtime actually writes today.
- **Durable agent protocols in AGENTS.md.** Four new sections (8 through 11) mandate the operational action layer contract, the three authority modes, the channel gateway inheritance from Hermes, and the Command Centre product name. Protocols apply to every agent operating on this repo regardless of session history.
- **CI pytest-suite job.** Runs the full `python -m pytest` suite (239 tests) on every push and pull request against main. Checks out aigovops as a sibling workspace so tool-registry tests and demo replay tests can resolve the plugins. Before this change only two test modules were gated in CI.

### Changed

- **[README.md](README.md) overhaul.** Flagship sentence narrowed to "Local-first AI governance runtime for audit-grade artifact production." Added an ASCII architecture map showing the four layers (operator surfaces, Hermes Agent runtime, AIGovClaw domain, AIGovOps plugin catalogue). Added a status matrix with explicit Works / Works (dependent on aigovops) / Planned / Not-yet-hardened states per component.
- **Replay test module naming.** Renamed `demos/audit-log/test_demo.py` to `test_audit_log_demo.py` and `demos/gap-assessment/test_demo.py` to `test_gap_assessment_demo.py` so pytest collects both without the "unique basename" conflict.

### Fixed

- **Demo plugin resolution.** `demos/*/run.py` now honors the `AIGOVOPS_PLUGINS_PATH` environment variable (matches the convention used by `tools/tests/test_registry.py` and the CI workflow), falling back to sibling directory and `~/Documents/CODING/aigovops` in that order. Previous hardcoded list caused CI failures for the audit-log demo replay.
- **Markdownlint violations.** Fenced code blocks now declare language (`text` for ASCII diagrams, `bash` for commands); bullet lists have blank separators.

### Internal

- `.gitignore` extended to exclude timestamped files under `demos/*/output/` so subsequent local demo runs do not show as untracked changes. One reference set per demo remains committed as the last known good result.
