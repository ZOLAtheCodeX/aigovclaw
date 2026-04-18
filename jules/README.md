# Jules Integration (AIGovClaw)

> **MAINTAINER TOOLING. Not a product feature.**
>
> This module is internal tooling for the AIGovOps maintainers (Zola + Claude Code). It is not distributed as part of the AIGovClaw runtime. End-users running AIGovClaw do not invoke, configure, or encounter Jules. The `dispatch_jules_session` tool is deliberately NOT registered in the Hermes tool registry. This module lives in the public repo for transparency; it is not a feature.
>
> Category: same as CI workflows, dependabot configuration, pre-commit hooks. Infrastructure for repository maintenance.

Operator-facing documentation for the Jules dispatcher. Jules is Google's autonomous async coding agent. This module wraps Jules as a background maintenance worker for the AIGovOps catalogue. For the full design rationale, see `docs/jules-integration-design.md`.

## Overview

Jules runs in isolated Ubuntu VMs, clones a target repo, applies changes, and opens a pull request. This module:

1. Persists `FlaggedIssue` records in `jules/flagged/` (one JSON file per issue).
2. Dispatches them to the Jules REST API at `https://jules.googleapis.com/v1alpha/`.
3. Polls activity feeds and advances the state machine defined in the design doc.
4. Handles failures per the decision tree in design Section 8.
5. Emits an ISO 42001 Clause 9.1 audit event on every terminal transition via the AIGovOps `audit-log-generator` plugin.

Jules reads `AGENTS.md` at the target repo root. Both `aigovclaw` and `aigovops` already carry one. Jules respects it.

## Prerequisites

1. `JULES_API_KEY` environment variable set. The dispatcher refuses to start without it.
2. `GITHUB_TOKEN` if the dispatcher-side workflows need to read or write GitHub state directly.
3. Write access to target repos via Jules account configuration (web UI). Jules never pushes to `main`; every change is a pull request.
4. Python 3.10 or later.
5. `requests` library (declared in `jules/requirements.txt`).

Set the key and check the value is present:

```bash
export JULES_API_KEY="your-key-here"
python3 -c "import os; assert os.environ.get('JULES_API_KEY'), 'not set'; print('ok')"
```

## Agent Skills

The 8 Jules maintenance playbooks under `jules/playbook/` are also published as Agent Skills in the open standard at `jules/skills/`. The two forms coexist:

- Flat `jules/playbook/*.md` files remain the input format for the Python dispatcher (`jules/dispatcher.py`). The dispatcher continues to read these. No dispatcher changes.
- `jules/skills/<name>/` is the cross-agent distribution form, compatible with Jules Skills, Claude Code Skills, Cursor, Gemini CLI, and Antigravity. Each skill directory contains `SKILL.md` (frontmatter + prose), `scripts/` (stale-check and post-check helpers), `resources/` (citation rules, prohibited-content lists), `assets/` (PR title, branch name, commit message templates), and a human-facing `README.md`.

Install into a target agent via `bash jules/skills/install.sh --target <agent>` where `<agent>` is one of `claude-code`, `cursor`, `gemini-cli`, `antigravity`, or `jules`. See `jules/skills/README.md` for the full catalog and compatibility matrix.

These skills are maintainer-scoped (same scope as the dispatcher itself). End-users of AIGovClaw do not invoke them.

## Quickstart

All commands assume the repo root is the working directory.

Dry-run dispatch (no API calls):

```bash
python3 -m jules.cli enqueue \
  --type "framework-drift" \
  --playbook framework-drift \
  --target-repo ZOLAtheCodeX/aigovops \
  --payload-json /path/to/payload.json

python3 -m jules.cli dispatch --dry-run --max-parallel 3
```

Real dispatch (requires `JULES_API_KEY`):

```bash
python3 -m jules.cli dispatch --max-parallel 3
python3 -m jules.cli poll
```

List and inspect:

```bash
python3 -m jules.cli list
python3 -m jules.cli list --state queued
python3 -m jules.cli show fi_abc123
```

## Architecture

Text diagram of the main components:

```text
+---------------------------------------+
| FlaggedIssue record (JSON file)       |
| jules/flagged/<id>.json               |
+---------------------------------------+
                 |
                 v
+---------------------------------------+
| Dispatcher                            |
|  - enqueue                            |
|  - dispatch_queued                    |
|  - poll_in_progress                   |
|  - handle_terminal_failure            |
|  - emit_audit_log                     |
+---------------------------------------+
        |                      |
        v                      v
+---------------+     +----------------------------+
| JulesClient   |     | AIGovClaw tool registry    |
| REST v1alpha  |     | -> audit-log-generator     |
+---------------+     +----------------------------+
        |
        v
+-----------------------------------------------+
| Jules cloud                                   |
|  - isolated VM clones target_repo             |
|  - reads AGENTS.md, STYLE.md, playbook .md    |
|  - applies changes, opens PR                  |
+-----------------------------------------------+
        |
        v
+-----------------------------------------------+
| Human reviews and merges PR on GitHub         |
+-----------------------------------------------+
        |
        v
+-----------------------------------------------+
| Dispatcher transitions issue to merged /      |
| rejected / escalated and emits audit event    |
+-----------------------------------------------+
```

State machine (design Section 3.2):

```text
flagged -> queued -> dispatched -> in-progress -> draft-pr -> reviewed -> merged
                                 \-> failed -> escalated
                                 \-> rejected
```

## Playbook catalog

All playbook prompt files live in `jules/playbook/`. Each one is self-contained because Jules has no conversation context. Each references `AGENTS.md` and `STYLE.md` at the target repo root.

1. `framework-drift.md` - correct framework text drift when an authoritative source is linked.
2. `test-coverage-gap.md` - add mechanical missing tests for a plugin.
3. `dep-bump.md` - patch or minor dependency bump if CI passes.
4. `citation-drift.md` - rewrite citations that do not match `STYLE.md`.
5. `markdown-lint.md` - fix markdown lint regressions without prose edits.
6. `new-plugin-scaffold.md` - scaffold a new plugin directory per `plugins/README.md`.
7. `link-toc.md` - fix broken internal anchors and missing TOC entries.
8. `prohibited-content-sweep.md` - remove em-dashes, emojis, hedging language.

Every playbook file includes the sections: Trigger, Prompt, Expected output, Success criteria, Citations required.

## Operations runbook

### Enqueueing an issue

Build a payload JSON matching the playbook's expected fields. For `framework-drift`:

```json
{
  "authoritative_source_url": "https://www.iso.org/standard/81230.html",
  "target_paths": ["plugins/bias-audit/SKILL.md"],
  "paragraphs": ["Section 2, second paragraph"],
  "max_files_changed": 1
}
```

Then:

```bash
python3 -m jules.cli enqueue \
  --type "framework-drift" \
  --playbook framework-drift \
  --target-repo ZOLAtheCodeX/aigovops \
  --payload-json payload.json
```

This creates a file under `jules/flagged/<id>.json` in state `queued`.

### Checking state

```bash
python3 -m jules.cli list
python3 -m jules.cli list --state in-progress
python3 -m jules.cli show <id>
```

### Advancing the queue

The dispatcher does not run as a daemon in this version. Operator runs `dispatch` and `poll` explicitly or wires them into cron. Example cron:

```text
*/5 * * * * cd /path/to/aigovclaw && python3 -m jules.cli dispatch --max-parallel 3
*/2 * * * * cd /path/to/aigovclaw && python3 -m jules.cli poll
```

### Reviewing and merging a PR

1. Jules opens a PR on the target repo.
2. Dispatcher sets issue state to `draft-pr` and records `pr_url`.
3. Operator reviews the PR on GitHub.
4. On merge, operator records the outcome:

```bash
python3 -m jules.cli show <id>
# once merged on GitHub, advance the record:
python3 -c "from jules.dispatcher import Dispatcher, FlaggedIssueStore; \
from pathlib import Path; \
s = FlaggedIssueStore(Path('jules')); \
i = s.load('<id>'); i.transition('reviewed'); i.transition('merged'); s.save(i)"
```

A later iteration of the CLI will collapse this into a single command.

### Resetting a stuck session

If a session appears stuck in `in-progress` and the Jules web UI shows it as complete:

1. Run `python3 -m jules.cli poll` to force a refresh.
2. If the issue is still stuck, cancel: `python3 -m jules.cli cancel <id>`. This transitions to `rejected` and emits an audit entry.
3. If the cancel fails, inspect the Jules web UI directly using the `session_url` from `show`.

### Escalations

When `retry_count` reaches 2 or a terminal failure class is detected, the dispatcher sets state to `escalated` and emits an audit entry. Operator reviews by running `python3 -m jules.cli list --state escalated` and deciding whether to rewrite the playbook, adjust the payload, or abandon the issue. Escalated issues are not retried automatically.

### Audit entries

Every terminal transition writes an audit entry via the AIGovOps `audit-log-generator` tool. The resulting `audit_event_id` is stored on the issue record. The audit log lives at `~/.hermes/memory/aigovclaw/audit/YYYY-MM.jsonl`, owned by the audit-log-generator plugin.

### Key rotation

Procedure (per design Section 6.3):

1. Generate a new key in the Jules web UI Settings page.
2. Update `JULES_API_KEY` in the environment or `.env`.
3. Restart any long-running dispatcher process.
4. Run one trivial dispatch to confirm the new key works.
5. Revoke the old key in the Jules web UI.

Target cadence: every 90 days, or immediately after any suspected exposure.

## Troubleshooting

### `ConfigurationError: JULES_API_KEY env var not set`

The dispatcher refuses to start without the key. Set the environment variable and retry. In tests, pass `client=None` to `Dispatcher` to run in dry mode without a key.

### `JulesApiError: 401`

Invalid or revoked API key. Rotate per the procedure above.

### `JulesApiError: 403`

Jules account does not have access to the target repo. Grant access in the Jules web UI and retry.

### `JulesApiError: 429`

Quota exceeded. Daily tier cap reached. Wait for the rolling 24-hour window to reset, or upgrade tier per design Section 10.

### `StateTransitionError: invalid transition X -> Y`

An operator attempted to advance a record along a path the state machine forbids. Inspect the record with `show`, then either route through a valid intermediate state (for example `draft-pr -> reviewed -> merged`) or escalate.

### Issue stuck in `dispatched` forever

Jules setup script failed or the Jules VM did not start. Cancel the issue and re-enqueue with a simpler payload. If repeated, the target repo likely has a missing setup script or non-standard build; fix that in the repo before re-dispatching.

### PR diff touches a forbidden file

This is a governance incident. Reject the PR in GitHub, transition the record to `rejected`, and file a dedicated audit entry. The prompt or the target repo's `AGENTS.md` needs a fix before re-running the same playbook.

### Lost the `session_url`

Jules session URLs can be reconstructed from the session id via the Jules web UI. The dispatcher stores only the id reliably; the URL is a convenience field that may be empty if the API response omitted it.

## Directory layout reference

```text
jules/
  README.md                       this file
  dispatcher.py                   Dispatcher, JulesClient, FlaggedIssueStore, FlaggedIssue
  cli.py                          command-line interface
  playbook/
    framework-drift.md
    test-coverage-gap.md
    dep-bump.md
    citation-drift.md
    markdown-lint.md
    new-plugin-scaffold.md
    link-toc.md
    prohibited-content-sweep.md
  schemas/
    flagged-issue.schema.json
    playbook-metadata.schema.json
  flagged/
    .gitkeep                      active records land here as JSON
  archive/
    .gitkeep                      terminal records rotated here monthly
  scheduled-tasks.md              mirror registry of web-UI scheduled tasks
  requirements.txt
  tests/
    test_dispatcher.py
```

## Non-goals

Documented in the design doc Section 12. In short: Jules never merges its own PR, never authors framework interpretation, never edits `AGENTS.md`, `SECURITY.md`, `LICENSE`, `persona/SOUL.md`, or the `tools:` block of `config/hermes.yaml`.
