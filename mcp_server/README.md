# AIGovClaw MCP Server

Exposes the 12 AIGovOps governance plugins as Model Context Protocol tools.
Any MCP-capable client (Claude Desktop, Cursor, Zed, future VerifyWise or
Vanta MCP adapters) can invoke AIGovOps plugins through this server.

## What it exposes

Every plugin from `aigovops/plugins/` is wrapped as an MCP tool. The catalogue
is not re-authored here; it is imported from
`aigovclaw.tools.aigovops_tools.PLUGIN_TOOL_DEFS`.

| Tool | Artifact | Source skill |
|---|---|---|
| generate_audit_log | audit-log-entry | iso42001 |
| generate_role_matrix | role-matrix | iso42001 |
| generate_risk_register | risk-register | iso42001 |
| generate_soa | soa | iso42001 |
| run_aisia | aisia | iso42001 |
| generate_nonconformity_register | nonconformity-register | iso42001 |
| generate_review_package | review-package | iso42001 |
| generate_metrics_report | metrics-report | nist-ai-rmf |
| generate_data_register | data-register | iso42001 |
| check_applicability | applicability-report | eu-ai-act |
| classify_risk_tier | risk-tier-classification | eu-ai-act |
| generate_gap_assessment | gap-assessment | iso42001 |

## Install

```bash
pip install -r mcp_server/requirements.txt
```

The only runtime dependency is the official `mcp` Python package. The plugins
themselves are pure standard-library Python.

## Run

```bash
python -m aigovclaw.mcp_server.server
```

The server speaks MCP over stdio. Launch it from a parent directory that has
`aigovclaw/` on `PYTHONPATH`, or run from inside `aigovclaw/` where the module
is self-resolving.

## Claude Desktop configuration

Add an entry to `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) or the equivalent on your platform:

```json
{
  "mcpServers": {
    "aigovops": {
      "command": "python",
      "args": ["-m", "aigovclaw.mcp_server.server"],
      "env": {
        "AIGOVOPS_PLUGINS_PATH": "/absolute/path/to/aigovops/plugins",
        "PYTHONPATH": "/absolute/path/to/parent-of-aigovclaw"
      }
    }
  }
}
```

See `config/mcp-servers.example.json` in this repository for a complete
example, including a commented stub showing how a future VerifyWise or Vanta
MCP adapter would slot in alongside.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| AIGOVOPS_PLUGINS_PATH | /Users/zola/Documents/CODING/aigovops/plugins | Filesystem path to the aigovops plugins directory. |
| AIGOVOPS_MCP_LOG_LEVEL | INFO | Log verbosity on stderr. Accepts any Python logging level. |
| PYTHONPATH | (unset) | Used by the client launcher to place the parent of `aigovclaw/` on the module search path. |

## Security posture

- Read-only. Every exposed tool has `x-aigovops-read-only: true`,
  `x-aigovops-concurrency-safe: true`, and `x-aigovops-destructive: false`
  MCP annotations mirroring the Hermes `Tool` safety flags.
- No network egress from plugins. Plugins are pure Python functions that take
  a dict, return a dict. They do not open sockets, do not read files outside
  their own module, and do not make HTTP calls.
- No file writes outside the return value. Persistence of outputs is the
  responsibility of the caller (a workflow, an adapter, or the MCP client).
- Input validation is enforced by the Hermes `ToolRegistry` validator before
  any plugin code runs. Invalid inputs produce an MCP error; they do not
  reach the plugin.
- Logs. Every invocation is logged to stderr with tool name, input size in
  bytes, output size in bytes, and duration. Payloads are never logged.

## Tests

```bash
python mcp_server/tests/test_server.py
```

Tests run standalone or under pytest. If the `mcp` package is not installed,
the tests skip gracefully with a printed message rather than reporting a
fake pass.
