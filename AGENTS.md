# AGENTS.md

Instructions for AI agents (Jules, Claude Code, Codex CLI, Cursor, and others) operating on this repository. Read top to bottom before any action. The authoritative cross-repository quality rules live in [aigovops/AGENTS.md](https://github.com/ZOLAtheCodeX/aigovops/blob/main/AGENTS.md). That file takes precedence where any rule in this file is ambiguous or silent.

## 1. Prohibited content (applies everywhere, no exceptions)

The following are not acceptable in any file, commit message, PR title, PR body, issue title, issue body, code comment, docstring, YAML value, or agent-generated output in this repository.

- **No emojis.** Not in PR titles, not in PR bodies, not in commit messages, not in issue templates, not in file names, not in markdown headings, not in code comments. Plain text only.
- **No em-dashes (the U+2014 character).** Use a colon, a comma, parentheses, or restructure.
- **No hedging language.** Specifically prohibited: `may want to consider`, `might be helpful to`, `could potentially`, `it is possible that`, `you might find`, `we suggest you might`.

If you are an automated agent and your default output style violates these rules, override your default.

## 2. Lane boundaries

This repository is a runtime configuration package. Two lanes:

### Tactical-layer lane (Jules, Copilot, any infrastructure agent)

- `install.sh` except the security-sensitive steps (Hermes verification, permission application). Changes to non-security steps are acceptable with an approved issue.
- `skills/` directory sync scripts and documentation. Skill content itself is sourced from [aigovops](https://github.com/ZOLAtheCodeX/aigovops); this directory is populated at install time.
- `config/hermes.yaml` outside the `tools:` security block. The `tools:` block (filesystem, shell, web, email, calendar permissions) is NOT autonomously editable.
- Workflow documentation improvements in `workflows/*.md` that clarify existing steps without changing their meaning.

### Reasoning-layer lane (Claude Code or a designated reasoning agent; no tactical-agent edits)

- `persona/SOUL.md` (the agent persona is a load-bearing trust artifact).
- `workflows/*.md` step sequences, quality gates, and output artifact specifications. Editorial clarifications to existing steps are dual-lane.
- This file (`AGENTS.md`).

## 3. Files that must NEVER be modified autonomously

These require a human-approved GitHub issue before any change, from any lane.

- `SECURITY.md`
- `LICENSE`
- `persona/SOUL.md`
- `config/hermes.yaml` `tools:` security block (the permission defaults for filesystem, shell, web, email, calendar).

## 4. Quality gates

Every PR must satisfy, regardless of lane or author:

1. No prohibited content (emojis, em-dashes, hedging) in title, body, commit messages, or changed files.
2. PR title follows `<type>: <imperative summary>` with `<type>` from `feat`, `fix`, `chore`, `docs`, `ci`, `test`, `refactor`, `security`. No emoji prefix.
3. Commits are signed off by the author or by the agent's configured author identity.
4. If touching `install.sh`, include a plain-language test note stating how the change was validated (local test, clean-machine test, or deferred to Phase 3).

## 5. What this repository is

AIGovClaw is the Hermes Agent configuration package for AIGovOps. It consumes the framework-agnostic catalogue at [aigovops](https://github.com/ZOLAtheCodeX/aigovops). This repository contains the installer, the agent persona, the workflow definitions, and the security-scoped Hermes configuration. It is not a library and does not export importable modules.

## 6. Authoritative quality standard

The canonical quality standard for all AIGovClaw outputs, and for any content written in this repository, is [aigovops/STYLE.md](https://github.com/ZOLAtheCodeX/aigovops/blob/main/STYLE.md). Read it before writing anything.

## 7. Cross-repository coordination

When changes here require corresponding changes in [aigovops](https://github.com/ZOLAtheCodeX/aigovops) (or vice versa), open a tracking issue in both repositories and link them. Do not merge half a coordinated change.

## 8. Operational Action Layer

AIGovClaw ships a layered operational action architecture. Do not reimplement any of it.

- `aigovclaw/action_executor/`: registry of action types (`file-update`, `mcp-push`, `notification`, `re-run-plugin`, `trigger-downstream`, `git-commit-and-push`), authority-policy resolver, executor with audit trail + snapshot + rollback, per-action rate limits, dry-run wrapper.
- `aigovclaw/agent_loop/`: PDCA orchestrator (`PDCACycle`) driving Plan-Do-Check-Act iterations. Inner loops: `GapResolutionLoop` (ReAct-style), `CascadeLoop` (depth-limited propagation), `ValidationLoop` (refine-until-clean).
- `config/authority-policy.yaml`: user-configurable per-(plugin, action) authority overrides.
- `hub/v2_server/`: HTTP API serving the Command Centre (task queue, approval workflow, PDCA routes).

If a task requires taking a side-effectful action (write a file, push to Notion, commit to a repo, send a notification), route it through the action-executor. Do not invoke shell commands or subprocess writers directly. See `aigovclaw/action_executor/README.md` if present, and the contract in `hub/v2_server/command_registry.py`.

## 9. Authority modes

Three modes, enforced by the executor regardless of caller:

- `ask-permission`: safe default. Action queues in the Command Centre approval queue; executes only after user approves.
- `take-resolving-action`: runs automatically if the action is reversible and the trigger is high-confidence. Ambiguous cases downgrade to ask-permission.
- `autonomous`: runs without approval within rate limits. Per-plugin opt-in only via `config/authority-policy.yaml` `autonomous_opt_ins`. Never a global default.

Hard invariants, enforced regardless of policy:

- `git-commit-and-push` is always `ask-permission`.
- Destructive actions (delete, hard-overwrite, `--force` variants) are never `take-resolving-action` eligible.
- External side-effect actions (MCP push, email, SMS) default to `ask-permission` unless explicitly overridden per (plugin, action).
- Autonomous mode requires the plugin to appear in `autonomous_opt_ins`. A missing entry forces downgrade to ask-permission.

Jules PRs are always reviewed by a human before merge. No self-merge.

## 10. Channel gateway

AIGovClaw inherits channel delivery from Hermes Agent's `gateway/platforms/`. Supported out-of-the-box: Slack, Discord, Telegram (two variants), Signal, Email, Matrix, Mattermost, WhatsApp, SMS, Webhook, Home Assistant, REST api_server, plus six APAC channels. Do not reimplement channel delivery.

- In-process: `hermes.gateway.delivery.deliver(channel, message, severity, source_plugin, request_id)` when AIGovClaw runs inside a Hermes Agent Python environment.
- Out-of-process: POST to `{HERMES_API_URL}/gateway/deliver` when the env var is set. Optional `HERMES_API_TOKEN` for Bearer auth.
- Unavailable: the notification handler raises `NotImplementedError` with an actionable message. No silent fallback on Hermes channels. Operator explicitly uses `local-file` or `stdout` for local-only delivery.

See `docs/channels.md`.

## 11. Product name: Command Centre

User-facing product name is "AIGovClaw Command Centre" (British spelling). Directory paths (`hub/`, `hub/v0/`, `hub/v1/`, `hub/v2/`, `hub/v2_server/`), Python module names (`hub.cli`, `hub.v2.cli`, `hub.v2_server.server`), and CLI subcommand names remain `hub` for backward compatibility. Rename only user-facing prose, UI strings, README headings, and documentation titles. Do not rename directories, modules, or CLI invocation paths.
