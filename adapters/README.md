# adapters/

Push-adapter layer for AIGovClaw. Each adapter translates canonical AIGovOps plugin output dicts into the schema of an external destination (a GRC platform, a structured workspace tool, an email digest, or a ticketing system) and pushes the translated artifact there.

Status: **design scaffold** for Phase 4. The adapter contract is defined below. Concrete adapter implementations (Notion, Archer, ServiceNow GRC, Drata, Vanta, Linear, Jira) land when the user selects a destination during onboarding.

## Why the adapter layer exists

AIGovClaw's plugins produce canonical artifact dicts (SoA rows, risk register rows, AISIA sections, KPI records, and so on) with stable field names. The dicts live locally in `~/.hermes/memory/aigovclaw/<artifact>/` as the source of record. To make the artifacts visible in the organization's existing GRC tooling, the adapter layer reads these dicts and pushes them to the user's selected destination in that platform's native schema.

The separation is deliberate. Plugins do not know about destinations. Adapters do not know about frameworks. If a new GRC platform emerges, one new adapter covers every existing plugin; if a new plugin lands, every existing adapter already handles it.

## Adapter contract

Every adapter exposes the following interface.

### Required

```python
class Adapter:
    """Push AIGovClaw artifacts to an external destination."""

    name: str  # kebab-case identifier, for example "notion"
    version: str  # semver, for example "0.1.0"

    def __init__(self, config: dict):
        """Initialize with user-supplied config (credentials, target URLs,
        schema overrides). Credentials are pulled from the Hermes secret
        store via the runtime, not embedded here."""

    def health_check(self) -> dict:
        """Return {status: 'ok' | 'degraded' | 'error', detail: str}.
        Called during installation and periodically by the runtime."""

    def push_artifact(self, artifact: dict, artifact_type: str) -> dict:
        """Translate and push a single artifact. Returns a dict with
        {status: 'ok' | 'error', destination_ref: str | None,
         error: str | None, pushed_at: ISO-8601-UTC}."""

    def supported_artifact_types(self) -> list[str]:
        """Return the list of artifact_type strings this adapter handles.
        Valid types: 'audit-log-entry', 'risk-register-row', 'SoA-row',
        'AISIA-section', 'role-matrix', 'review-minutes',
        'nonconformity-record', 'KPI', 'gap-assessment'."""
```

### Optional

```python
    def pull_feedback(self, since: str) -> list[dict]:
        """Pull back changes the user made in the external platform since
        the supplied timestamp, so AIGovClaw's local source of record
        stays consistent. Not every platform supports round-trip sync;
        adapters that do not should raise NotImplementedError here."""

    def batch_push(self, artifacts: list[tuple[dict, str]]) -> list[dict]:
        """Push multiple artifacts in one operation when the destination
        supports batch APIs. Default implementation calls push_artifact
        in a loop."""
```

## Action-item classification on every push

Every pushed artifact carries a user-facing tag derived from the artifact's warnings and the organization's threshold policy:

- `action-required-human`: the artifact contains warnings the agent cannot resolve autonomously (missing owner, ambiguous classification, blocked-for-review items). The human needs to act.
- `completed-autonomously-high-confidence`: the artifact is complete, warnings are absent or cosmetic, and the classification or scoring is grounded in explicit evidence. No action required; informational only.
- `completed-autonomously-low-confidence`: the artifact is complete but the underlying evidence is thin or the framework guidance is ambiguous. The human should review but is not blocked.

The tag drives rendering on the destination platform: `action-required-human` items land in a dedicated queue; `completed-autonomously-high-confidence` items land in a log or digest; `completed-autonomously-low-confidence` items land in a review queue with lower priority.

## Onboarding flow (Phase 4)

At `./install.sh` time, the user selects their preferred adapter or adapters. The installer:

1. Lists available adapters from this directory.
2. Prompts the user for destination configuration (Notion workspace URL and database ID, Archer endpoint and credentials, and so on).
3. Validates connection via `health_check()`.
4. Registers the adapter in `config/hermes.yaml` under an `adapters:` block.
5. Writes a test artifact to confirm round-trip.

At runtime, the agent's workflow emissions route through every registered adapter that supports the artifact's type. Destinations receive the full artifact, not a digest; auditors need evidence, not summaries.

## Non-goals of the adapter layer

- Adapters do NOT modify artifact content. Translation is schema mapping only; the data is immutable in transit.
- Adapters do NOT filter items. Every artifact the plugin produces goes through. The human-facing platform handles prioritization.
- Adapters do NOT retry on the agent's behalf without explicit user authorization. A push failure is logged; whether to retry is a user decision per AGENTS.md Section 3 "behaviors refused regardless of instruction" (no silent retry on failure).
- Adapters do NOT cross-write across destinations. If a user switches from Notion to Drata, prior Notion pushes stay in Notion; new artifacts go to Drata. Migration is a separate tool, not an adapter responsibility.

## Planned concrete adapters

The following adapters will be implemented in Phase 4 as user demand confirms them. Each will live in its own subdirectory with `adapter.py`, `README.md`, and tests.

| Adapter | Destination | Priority | Notes |
|---|---|---|---|
| `local-filesystem` | the existing `~/.hermes/memory/aigovclaw/` write path | first | Null adapter; already implicit in every workflow. Formalizes the baseline. |
| `notion` | Notion workspace databases | high | Covers personal and small-team deployments. Schema per database. |
| `linear` | Linear issues | medium | Action-required items become issues; other items become comments or labels. |
| `drata` | Drata GRC platform | medium | API-based push; action items become tasks. |
| `vanta` | Vanta GRC platform | medium | Similar to Drata. |
| `servicenow-grc` | ServiceNow GRC module | low-medium | Enterprise deployments. |
| `archer` | Archer GRC | low | Enterprise deployments. |
| `email-digest` | SMTP summary emails | low | Fallback for environments with no primary GRC surface. |

## Security posture

Adapters handle the most security-sensitive step in the entire AIGovClaw flow: they send governance artifacts to external systems. Accordingly:

- Every adapter push emits an audit-log entry citing `ISO/IEC 42001:2023, Clause 7.5.3` (distribution) naming the adapter, the destination, and the artifact pushed.
- Credentials are never stored in this directory. Every adapter reads from the Hermes secret store per `config/hermes.yaml` references. Hardcoded credentials in an adapter are a security bug blocking merge.
- Adapters run in the same Hermes permission posture as the rest of AIGovClaw. A tier-restricted permission for external network writes is appropriate; the default posture permits outbound HTTPS to the configured destinations only.
- Health checks run in the background; failures surface to the review queue with the destination name and the error detail (never the credential).
- On adapter removal (user decides to stop syncing to a destination), the adapter leaves historical pushes in place at the destination and stops new pushes. No destructive cleanup.

## Cross-repository coordination

Adapter contract changes require coordinated updates with plugin output schemas. If a plugin field rename would break an adapter's schema mapping, the plugin version bumps (AGENT_SIGNATURE changes) and every registered adapter is checked for compatibility before the plugin lands on main.
