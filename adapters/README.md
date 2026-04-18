# adapters/

Artifact distribution layer for AIGovClaw. Canonical AIGovOps plugin output dicts (source of record under `~/.hermes/memory/aigovclaw/`) are routed to external destinations so that governance artifacts land where the organization already reads them.

## Design decision: MCP-first

AIGovClaw routes artifacts through [Model Context Protocol (MCP)](https://modelcontextprotocol.io) servers rather than implementing destination-specific HTTP adapters in-house. Rationale:

1. **Reuse over reinvention.** MCP servers already exist for Notion, Linear, Google Drive, GitHub, Gmail, and dozens of other destinations. Writing custom Python clients for each would duplicate work that the MCP ecosystem has already done better.
2. **Credential handling.** MCP servers handle their own auth against destination APIs. AIGovClaw never touches destination credentials; the Hermes harness invokes MCP tools through the protocol, and the MCP server authenticates on its own.
3. **Destination schema drift is upstream's problem.** When Notion's API changes, the Notion MCP server updates. AIGovClaw keeps its artifact schema stable and translates at the MCP-tool-invocation boundary.
4. **User onboarding is simpler.** Users configure MCP servers once in their Hermes environment; AIGovClaw inherits every configured server as a potential destination.

## The router's job

This directory contains one working adapter (`local-filesystem/`, the source-of-record baseline) and one router (`mcp/`). The router translates AIGovClaw artifact dicts into MCP tool-invocation specifications the Hermes harness executes.

The router does NOT call destinations directly. It produces:

```python
[
    {
        "mcp_server": "notion",
        "tool_name": "notion-create-page",
        "arguments": {
            "parent": {"database_id": "<user-configured>"},
            "properties": { ... translated from the artifact ... },
            ...
        },
        "action_tag": "action-required-human",  # or high/low confidence
        "source_artifact_type": "risk-register-row",
    },
    ...
]
```

The Hermes harness reads this list and invokes the MCP tools in sequence (or in parallel where the tools are concurrency-safe). Success and failure for each invocation are logged to `~/.hermes/memory/aigovclaw/audit-log/` per the audit-log workflow.

## Concrete adapters in this directory

| Directory | Purpose | Status |
|---|---|---|
| `local-filesystem/` | Baseline adapter that writes artifacts to `~/.hermes/memory/aigovclaw/<artifact-type>/`. The source of record; every AIGovClaw workflow writes here first. | working |
| `mcp/` | Router that translates artifacts into MCP tool-invocation specifications. Configuration-driven; the user declares which artifact types route to which MCP tools. | working |

## Action-item classification

Every artifact pushed through any adapter carries an action-item tag derived from the artifact's warnings and organizational threshold policy:

- `action-required-human`: the artifact contains warnings the agent cannot resolve autonomously. The human needs to act. Rendered on the destination as a high-priority item or in a dedicated queue.
- `completed-autonomously-high-confidence`: complete, warnings absent or cosmetic, classification grounded in explicit evidence. Informational.
- `completed-autonomously-low-confidence`: complete but the underlying evidence is thin or framework guidance is ambiguous. Human should review but is not blocked.

The tag is computed by the router from the artifact dict before routing. Destinations receive it as a property on every pushed page or record.

## Configuration model

Adapter configuration lives in `config/adapters.yaml` alongside the Hermes runtime config. Structure:

```yaml
adapters:
  local-filesystem:
    enabled: true          # source of record, always on
    base_path: ~/.hermes/memory/aigovclaw

  mcp:
    enabled: true
    routes:
      risk-register-row:
        - mcp_server: notion
          tool_name: notion-create-page
          arguments:
            parent: {database_id: "<your-notion-risk-register-db-id>"}
          property_mapping:
            Title: "description"
            System: "system_name"
            Category: "category"
            Likelihood: "likelihood"
            Impact: "impact"
            Residual: "residual_score"
            Owner: "owner_role"

      nonconformity-record:
        - mcp_server: linear
          tool_name: linear-create-issue
          arguments:
            team: "<your-linear-team-id>"
          property_mapping:
            title: "description"
            state: "status"
            description: "root_cause"

      audit-log-entry:
        - mcp_server: google-drive
          tool_name: google-drive-create-document
          arguments:
            folder_id: "<your-drive-folder-id>"

      # Any artifact type can have zero, one, or many routes.
      # Routes are non-exclusive: a risk-register-row can land in
      # Notion AND Linear simultaneously.
```

The router ships with no default routes; users configure per their MCP setup.

## Onboarding

1. User configures MCP servers in their Hermes environment (outside AIGovClaw scope).
2. User creates `config/adapters.yaml` with routes for the artifact types they care about.
3. AIGovClaw workflows emit artifacts; the MCP router translates each into tool-invocation specs; Hermes executes.

There is no `aigovclaw install adapter notion` step. Adapters are configuration, not installation.

## Security

Adapters handle the most security-sensitive step in AIGovClaw: distributing governance artifacts to external systems. Defenses:

- Every MCP-routed push emits an audit-log entry citing `ISO/IEC 42001:2023, Clause 7.5.3` (distribution), naming the MCP server, the tool, and the artifact identifier.
- Credentials never appear in `config/adapters.yaml`. They live in the MCP server's own configuration (per-server, typically in OS keychain or environment variables).
- Invocation failures surface to the review queue with the MCP server name and tool name; credentials never appear in error messages.
- On adapter removal (user decides to stop syncing to an MCP destination), historical pushes remain at the destination. No destructive cleanup.

## Cross-repository coordination

Adapter configuration changes are aigovclaw-local (no aigovops impact). Plugin output schema changes (which affect the `property_mapping` translators) require coordinated adapter-config updates and should bump the plugin `AGENT_SIGNATURE` per the AIGovOps plugin-author contract.

## What this directory does NOT include

- **Destination-specific Python HTTP clients.** Those belong in the MCP server ecosystem, not here.
- **Credentials, tokens, or API keys.** Those live in the MCP server's own config.
- **Retry or queue infrastructure.** MCP tool invocation is the harness's responsibility. A failed invocation is logged; retry policy is organizational policy, not hardcoded here.
