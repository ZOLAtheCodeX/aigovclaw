# Jules Integration Design Proposal

Status: DRAFT for user review. Not approved. No implementation yet.
Owner: Zola Valashiya
Target repos: `aigovclaw` (this repo) and `aigovops` (sibling catalogue)
Date: 2026-04-18

This document proposes how Google Jules is wired into AIGovClaw as a background maintenance worker for the AIGovOps catalogue. It covers role split, dispatch model, playbook entries, failure handling, governance audit, cost, open questions, non-goals, and a phased rollout. It contains no code. After approval, implementation lands in a separate PR.

## 1. Objective

### 1.1 Why Jules

AIGovClaw is a Hermes Agent runtime config that invokes AIGovOps plugins as tools. The catalogue has 12 plugins. Each plugin carries a `SKILL.md`, an artifact template, a schema, and a test fixture. As frameworks shift (ISO 42001, NIST AI RMF, EU AI Act), the plugin text drifts from authoritative sources. Test coverage gaps accumulate. Dependency versions go stale. Citation formats wander from `STYLE.md`.

Claude Code is the right tool for foreground work: architecture, new plugins, human-in-the-loop reasoning, cross-repo design. It is the wrong tool for rote maintenance that a deterministic async worker can do overnight in parallel VMs.

Jules fills that gap. Jules is Google's autonomous async coding agent. It runs in isolated Ubuntu VMs, clones the repo, applies changes, and opens a PR. It auto-picks up `AGENTS.md`. It has a REST API. It supports scheduled tasks via web UI.

### 1.2 In scope for Jules

Jules is restricted to a defined set of low-judgment, high-volume, verifiable maintenance work:

1. Framework text drift corrections when an authoritative source is linked.
2. Test coverage gap fills where the gap is mechanical (missing assertion category, missing fixture, missing edge case).
3. Dependency version bumps that pass CI without API changes.
4. Citation format fixes against `STYLE.md` rules.
5. Markdown lint regressions.
6. Plugin scaffolding from a skeleton contract (new plugin directory, empty `SKILL.md`, schema stub, test stub).
7. Docs-only refactors (TOC regeneration, link validation, anchor drift).

### 1.3 Out of scope for Jules

Jules does not do any of the following, ever:

1. Author framework interpretation. No new `SKILL.md` body text, no new control mappings, no new risk taxonomy entries.
2. Edit `SECURITY.md`, `LICENSE`, `persona/SOUL.md`, or the `tools:` security block in `config/hermes.yaml`. These are hard-blocked in `AGENTS.md` and Jules must respect that.
3. Author `persona/` content in either repo.
4. Touch production artifacts (a plugin run output promoted to client deliverable status).
5. Make release decisions. No version bumps in package metadata, no tagging, no publishing.
6. Merge its own PRs. Every Jules PR requires a human merge.
7. Make cross-repo coordinated changes without an existing tracking issue pair (per `AGENTS.md` Section 7).

## 2. Role split

Three actors operate against these repos. The split is load-bearing: if Jules drifts into Claude Code's lane or human's lane, the governance posture breaks.

| Concern                                     | Claude Code     | Jules           | Human (Zola)    |
|---------------------------------------------|-----------------|-----------------|-----------------|
| New plugin design (taxonomy, schema, contract) | Owns         | No              | Approves        |
| New plugin scaffolding (directory, empty files) | Option      | Owns (playbook) | Approves        |
| `SKILL.md` body text (framework interpretation) | Owns         | No              | Approves        |
| Framework text drift (one-line corrections, linked source) | Option | Owns            | Approves PR     |
| Plugin schema evolution                     | Owns            | No              | Approves        |
| Test fixture design                         | Owns            | No              | Approves        |
| Test coverage gap fill (mechanical)         | Option          | Owns            | Approves PR     |
| Dependency bumps (patch, minor)             | Option          | Owns            | Approves PR     |
| Dependency bumps (major, API change)        | Owns            | No              | Approves        |
| Citation format fixes (STYLE.md)            | Option          | Owns            | Approves PR     |
| Markdown lint fixes                         | Option          | Owns            | Auto-merge allowed for lint-only |
| TOC regeneration, link validation           | Option          | Owns            | Auto-merge allowed |
| `AGENTS.md` edits                           | Owns            | No              | Approves        |
| `persona/SOUL.md` edits                     | Owns            | No              | Approves        |
| `config/hermes.yaml` `tools:` block         | No              | No              | Human-only      |
| `SECURITY.md`, `LICENSE`                    | No              | No              | Human-only      |
| Cross-repo coordinated change               | Owns design     | Executes leaf edits only after issue pair exists | Approves issue pair |
| Audit log entry for every governance event  | Triggers writes | Triggers writes | Reads, signs off |
| Release tagging, version bumps in metadata  | No              | No              | Human-only      |
| Merge to `main`                             | No              | No              | Human-only      |
| Final PR review and merge                   | No              | No              | Human-only      |

Rule of thumb: Claude Code designs, Jules executes mechanical work, Zola approves and merges. No agent merges its own PR.

## 3. Dispatch model

### 3.1 Flagged-issue record

The dispatcher consumes a data type called `FlaggedIssue`. This is a future JSON record, stored as a file in `aigovclaw/jules/flagged/` (one file per issue) or an equivalent store. Claude Code and human review produce these records. Jules never creates them.

Fields:

| Field                | Type              | Required | Notes |
|----------------------|-------------------|----------|-------|
| `id`                 | string (ULID)     | yes      | Stable identifier. |
| `created_at`         | ISO 8601          | yes      | Record creation timestamp. |
| `created_by`         | enum              | yes      | `claude-code`, `human`, `scheduled`. |
| `playbook`           | enum              | yes      | One of the playbook entries in section 4. |
| `target_repo`        | string            | yes      | `ZOLAtheCodeX/aigovops` or `ZOLAtheCodeX/aigovclaw`. |
| `target_paths`       | string[]          | yes      | Files or globs Jules is permitted to touch. |
| `scope_note`         | string            | yes      | Short plain-language scope, one sentence. |
| `authoritative_source` | string (URL)    | conditional | Required for framework-drift playbook. Required for citation-drift if source is a spec. |
| `success_criteria`   | string[]          | yes      | Machine-checkable assertions. Each must be verifiable from the PR diff and CI output. |
| `max_files_changed`  | integer           | yes      | Hard cap. Default 5. |
| `requires_human_merge` | boolean         | yes      | Default `true`. Only markdown-lint and TOC regeneration may set `false`. |
| `priority`           | enum              | yes      | `low`, `normal`, `high`. Affects dispatch order, not VM allocation. |
| `state`              | enum              | yes      | See state machine in 3.2. |
| `jules_session_id`   | string            | conditional | Populated after dispatch. |
| `jules_session_url`  | string            | conditional | Web UI link for human inspection. |
| `pr_url`             | string            | conditional | Populated after PR opens. |
| `audit_event_id`     | string            | conditional | Populated after audit-log-generator writes the governance event. |
| `failure_reason`     | string            | conditional | Populated on terminal failure. |
| `retry_count`        | integer           | yes      | Default 0. Hard cap at 2 before escalation. |

### 3.2 State machine

```text
flagged -> queued -> dispatched -> in-progress -> draft-pr -> reviewed -> merged
                                \-> failed -> escalated
                                \-> rejected
```

Transitions:

| From         | To            | Trigger |
|--------------|---------------|---------|
| `flagged`    | `queued`      | Dispatcher validates record against schema and checks quota. |
| `queued`     | `dispatched`  | Dispatcher calls `POST /sessions` on Jules API. Session ID returned. |
| `dispatched` | `in-progress` | Dispatcher polls `/sessions/{id}/activities` and observes first non-setup activity. |
| `in-progress`| `draft-pr`    | Jules opens a PR. Dispatcher captures `pr_url` from activity feed outputs. |
| `draft-pr`   | `reviewed`    | Human reviews PR. Record updated by CLI or web UI. |
| `reviewed`   | `merged`      | Human merges PR. Post-merge hook triggers audit-log-generator. |
| `in-progress`| `failed`      | Jules reports terminal failure in activity feed (auto-retry exhausted). |
| `failed`     | `queued`      | Dispatcher auto-retries if `retry_count < 2`. |
| `failed`     | `escalated`   | `retry_count` reached 2, or failure class is non-retriable. |
| `draft-pr`   | `rejected`    | Human rejects PR. Record closed, audit entry written with rejection reason. |

Invariants:

- A record in `merged` or `rejected` is terminal. No further transitions.
- A record in `escalated` requires human action. Dispatcher does not act on escalated records.
- `audit_event_id` must be populated before a record transitions to `merged` or `rejected`. This is the governance audit hook (see section 9).

### 3.3 Dispatcher responsibilities

The dispatcher is a small process that:

1. Reads new `FlaggedIssue` records from `aigovclaw/jules/flagged/`.
2. Validates each against `schemas/flagged-issue.schema.json`.
3. Renders the prompt from the matching playbook template.
4. Calls Jules REST API to create a session with `requirePlanApproval: true`.
5. Polls `/sessions/{id}/activities` at a moderate cadence (15 seconds during active session, 60 seconds during plan-wait).
6. Approves the plan if and only if the plan matches policy rules for that playbook (see section 4).
7. Updates the record as state transitions.
8. On terminal failure, applies the decision tree in section 8.
9. On successful merge, triggers the audit-log-generator plugin (see section 9).

The dispatcher is not written in this document. A separate PR will implement it after this design is approved.

## 4. Prompt templates (playbook)

Each playbook entry lives at `aigovclaw/jules/playbook/<entry-name>.md`. Jules loads it as the session prompt. The playbook is versioned with the repo.

Each entry follows this structure:

- **Trigger.** What condition creates a `FlaggedIssue` with this playbook.
- **Prompt template path.** Repo-relative path to the prompt file.
- **Expected output.** What the PR looks like.
- **Success criteria.** Mechanical assertions the dispatcher checks before marking `reviewed`.
- **Plan-approval rule.** What Jules's generated plan must look like for the dispatcher to auto-approve. If the plan does not match, escalate to human.

### 4.1 Framework text drift

| Field | Value |
|---|---|
| Trigger | Claude Code or a scheduled scan finds a published update to ISO 42001, NIST AI RMF, or EU AI Act that invalidates text in a plugin's `SKILL.md`. `authoritative_source` is a URL to the updated spec section. |
| Prompt template path | `aigovclaw/jules/playbook/framework-drift.md` |
| Expected output | A PR that edits exactly the targeted `SKILL.md` paragraphs to match the authoritative source. Citations updated. No new interpretation, no structural rewrites. |
| Success criteria | (a) Diff touches only files in `target_paths`. (b) Diff line count under `max_files_changed * 40`. (c) CI passes. (d) Grep for prohibited content (emoji, em-dash, hedging) returns zero. (e) Citation format matches `STYLE.md`. |
| Plan-approval rule | Plan must list at most `max_files_changed` files. Plan must not propose adding new plugins. Plan must not propose editing `AGENTS.md`, `persona/`, `SECURITY.md`, or `config/hermes.yaml`. |

### 4.2 Test coverage gap

| Field | Value |
|---|---|
| Trigger | A plugin has fewer than the minimum assertion categories (to be set per plugin; default 5). Gap identified by Claude Code review or scheduled coverage scan. |
| Prompt template path | `aigovclaw/jules/playbook/test-coverage-gap.md` |
| Expected output | A PR that adds missing test cases in `plugins/<name>/tests/`. No changes to plugin source, schema, or `SKILL.md`. |
| Success criteria | (a) New tests exist in `plugins/<name>/tests/`. (b) All new tests pass. (c) Existing tests still pass. (d) Test names match naming convention in `CONTRIBUTING.md`. (e) No emoji, no em-dash, no hedging in test docstrings. |
| Plan-approval rule | Plan must scope to `plugins/<name>/tests/` only. Plan must not propose editing the plugin under test. |

### 4.3 Dependency bump

| Field | Value |
|---|---|
| Trigger | A dependency has a new patch or minor version. Scheduled weekly scan surfaces candidates. Major-version bumps never use this playbook. |
| Prompt template path | `aigovclaw/jules/playbook/dep-bump.md` |
| Expected output | A PR with exactly one dependency version bump, CI green. Lockfile updated. Changelog entry added if the repo uses one. |
| Success criteria | (a) Diff touches only `package.json`, `package-lock.json`, `requirements.txt`, `pyproject.toml`, or equivalent. (b) CI passes on all jobs. (c) No source-file edits. |
| Plan-approval rule | Plan must name exactly one dependency. Plan must declare the jump is patch or minor. If Jules's plan reveals the bump requires source changes, escalate to human. |

### 4.4 Citation format drift

| Field | Value |
|---|---|
| Trigger | Scheduled grep against `STYLE.md` citation rules finds a citation in the wrong format. |
| Prompt template path | `aigovclaw/jules/playbook/citation-drift.md` |
| Expected output | A PR that rewrites the offending citations in place. Format matches `STYLE.md` examples exactly. |
| Success criteria | (a) Grep for the anti-pattern returns zero after the PR. (b) Grep for the preferred pattern returns at least as many hits as before. (c) No semantic text changes outside the citation token itself. |
| Plan-approval rule | Plan must list citation edits only. Plan must not propose adding new sources. |

### 4.5 Markdown lint regression

| Field | Value |
|---|---|
| Trigger | CI markdown lint job fails on `main` or the scheduled nightly lint pass flags warnings. |
| Prompt template path | `aigovclaw/jules/playbook/markdown-lint.md` |
| Expected output | A PR that applies lint fixes. No content changes. |
| Success criteria | (a) Lint job passes after the PR. (b) Diff is whitespace, heading level, or list-marker changes only. (c) No paragraph-level text edits. |
| Plan-approval rule | Plan must explicitly state "lint-only". Plan must not propose content edits. This playbook may set `requires_human_merge: false` for fully automated merge. |

### 4.6 New plugin scaffolding

| Field | Value |
|---|---|
| Trigger | Human or Claude Code flags a new plugin name and artifact type. Claude Code has already designed the plugin contract. Jules scaffolds the directory structure per `plugins/README.md`. |
| Prompt template path | `aigovclaw/jules/playbook/new-plugin-scaffold.md` |
| Expected output | A PR that creates `plugins/<name>/` with: empty `SKILL.md` matching the template shape, stub `schema.json`, stub test directory with one placeholder test, and entry in the plugin index if one exists. No content in `SKILL.md` body beyond the shape. |
| Success criteria | (a) Directory structure matches `plugins/README.md` contract exactly. (b) `schema.json` validates against the plugin-schema meta-schema. (c) Placeholder test is marked as skipped or pending. (d) `SKILL.md` contains only the section headers and a TODO marker. No framework interpretation. |
| Plan-approval rule | Plan must explicitly state "scaffold-only". Plan must not propose filling in `SKILL.md` body. If Jules's plan includes content generation, escalate to human. |

### 4.7 Link validation and TOC regeneration

| Field | Value |
|---|---|
| Trigger | Scheduled nightly link checker finds broken internal anchors or missing TOC entries. |
| Prompt template path | `aigovclaw/jules/playbook/link-toc.md` |
| Expected output | A PR that fixes broken anchors, regenerates TOCs, updates cross-references. No content changes. |
| Success criteria | (a) Link checker passes after the PR. (b) Diff is link-token and TOC-block changes only. |
| Plan-approval rule | Plan must state "link-and-toc only". May set `requires_human_merge: false`. |

### 4.8 Prohibited-content sweep

| Field | Value |
|---|---|
| Trigger | Scheduled nightly grep finds an emoji, em-dash, or hedging phrase introduced since last sweep. |
| Prompt template path | `aigovclaw/jules/playbook/prohibited-content-sweep.md` |
| Expected output | A PR that removes or replaces the prohibited content per `AGENTS.md` Section 1. |
| Success criteria | (a) Grep for each prohibited pattern returns zero after the PR. (b) Replacement preserves sentence meaning. (c) No net content loss. |
| Plan-approval rule | Plan must list exact replacements per pattern. If replacement would alter meaning materially, escalate to human. |

## 5. Scheduled vs event-triggered

### 5.1 Dual-dispatch model

Jules ships an official GitHub Action, `google-labs-code/jules-invoke@v1`. This collapses the scheduled-vs-event distinction for any dispatch that can originate inside GitHub: GitHub Actions cron, `issues.labeled`, `workflow_run`, `workflow_dispatch`, and `issues.closed` events are all programmatic entry points, and all of them compose cleanly with `jules-invoke@v1`. This sidesteps the Jules web-UI-only scheduled-tasks limitation entirely.

Two dispatch paths exist. Each playbook is assigned one (and only one) primary path.

1. **GitHub Actions via `jules-invoke@v1` (primary path).** Used for all playbooks whose triggering condition can be expressed as a GitHub event or a cron expression. Versioned in `.github/workflows/jules-<playbook>.yml` in the target repo. Programmatic, auditable via the Actions log, concurrency-capped via the workflow `concurrency:` keyword. Secrets via GitHub Secrets. This is the default.

2. **Direct REST API dispatch via Python dispatcher (secondary path).** Used for dispatches that originate outside GitHub or that require cross-repo orchestration. Specifically: (a) ad-hoc human-authored `FlaggedIssue` records, (b) cross-repo coordinated dispatches that must open paired issues before Jules runs, (c) dispatches originating from the AIGovClaw Hermes agent when it discovers a governance gap during a reasoning loop, (d) re-dispatch after a failed GH Actions run where the retry logic lives in the dispatcher. The dispatcher calls Jules REST with `automationMode: "AUTO_CREATE_PR"` and `requirePlanApproval: true`.

### 5.2 Split

| Playbook entry | Primary dispatch path | Trigger |
|---|---|---|
| 4.1 Framework drift | GitHub Actions | Weekly cron. Secondary: Python dispatcher on human-flagged `authoritative_source` change. |
| 4.2 Test coverage gap | GitHub Actions | `workflow_run` on CI completion where test count falls below the per-plugin threshold. |
| 4.3 Dependency bump | GitHub Actions | Weekly cron. Optional backup event on security advisory webhook. |
| 4.4 Citation drift | GitHub Actions | Weekly cron. Secondary: Python dispatcher on-demand when `STYLE.md` itself changes. |
| 4.5 Markdown lint | GitHub Actions | `workflow_run` on markdownlint CI failure. |
| 4.6 New plugin scaffold | Python dispatcher only | Human-initiated FlaggedIssue. Never scheduled. Never event-triggered from inside GitHub. |
| 4.7 Link and TOC | GitHub Actions | Weekly cron. |
| 4.8 Prohibited-content sweep | GitHub Actions | Weekly cron. |

### 5.3 Why this split

- Scheduled-cadence playbooks belong on GH Actions cron because cron is cheap, programmatic, and the workflow file is the source of truth. No mirror registry required.
- CI-reactive playbooks (4.2, 4.5) belong on `workflow_run` because the trigger condition is literally "CI just failed in a specific way". Any other dispatch path would poll or duplicate the signal.
- 4.6 (new plugin scaffold) is human-initiated and must carry a human-authored `FlaggedIssue` with the plugin contract already designed. That cannot be expressed as a GitHub event, and it must flow through the dispatcher so the record is validated against `schemas/flagged-issue.schema.json` before Jules runs.
- 4.1 and 4.4 get dual paths because framework updates and style-guide updates can surface either through a scheduled source-check or through an out-of-band human decision.

### 5.4 Workflow-file source of truth

For every GH Actions-dispatched playbook, the workflow file at `.github/workflows/jules-<playbook>.yml` is the single source of truth for cadence, trigger, and prompt pointer. Changing cadence is a PR against that file. No external registry is required. No web-UI scheduled tasks exist. Section 14 specifies the workflow-file standard.

## 6. Authentication and secrets

### 6.1 API key placement

Jules API keys live in `.env` at the repo root. The `.env` file is never committed. `.gitignore` already excludes `.env`. The dispatcher reads `JULES_API_KEY` from the environment at startup and refuses to start if unset.

### 6.2 Header injection

All Jules API calls include `X-Goog-Api-Key: ${JULES_API_KEY}`. No other auth method is supported by Jules at this time. Bearer tokens and OAuth are not used here.

### 6.3 Rotation

Jules allows a maximum of three active keys per account. Rotation procedure:

1. Generate a new key in the Jules web UI Settings page.
2. Update `.env` on the dispatcher host.
3. Restart the dispatcher process.
4. Confirm one dispatched session succeeds with the new key.
5. Revoke the old key in the Jules web UI Settings page.

Target rotation cadence: every 90 days, or immediately after any suspected exposure.

### 6.4 Other secrets

The dispatcher also needs a GitHub token to read `FlaggedIssue` records if they are stored as GitHub issues (see open question 11.3) and to read PR state. Placement and rotation match the `JULES_API_KEY` pattern. All secrets loaded from `.env`. None committed.

## 7. Directory layout

Proposed structure inside `aigovclaw`:

```text
aigovclaw/
  jules/
    README.md                       human-readable overview of this module
    dispatcher.py                   future, not part of this doc
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
      .gitkeep                      FlaggedIssue records land here as JSON
    archive/
      YYYY-MM/                      merged and rejected records, rotated monthly
    scheduled-tasks.md              mirror registry of Jules web-UI scheduled tasks
  docs/
    jules-integration-design.md     this document
```

Notes:

- `jules/flagged/` holds active records only. Merged and rejected records move to `jules/archive/YYYY-MM/` monthly. This keeps active queue small and preserves history.
- `jules/playbook/` is the source of truth for Jules behavior. Scheduled tasks in the web UI only reference these paths.
- Schemas are versioned alongside playbooks. Breaking schema changes require bumping all affected playbook entries.
- `jules/README.md` is a short operator-facing doc (how to add a playbook, how to flag an issue, how to rotate a key). It is not this design doc.

## 8. Failure handling

### 8.1 Jules-internal retries

Jules auto-retries transient failures:

- Network interruptions.
- Temporary dependency installation failures.
- Extended dependency resolution times.

These are invisible to the dispatcher unless they surface as activity-feed entries. The dispatcher does not intervene during Jules's own retry cycle.

### 8.2 Terminal failure detection

The dispatcher detects terminal failure by polling `/sessions/{id}/activities`. A session is terminally failed when the activity feed shows a failure entry and no further activity occurs within a grace window (default 120 seconds).

Common terminal failure causes documented by Jules:

1. Absent or deficient environment setup script.
2. Ambiguous or overly broad prompt.
3. Non-standard build workflow.
4. Long-running background process in setup.

For AIGovOps, (1) and (3) should not occur (the repos have standard Node and Python setups with known scripts). (2) is a prompt-quality signal, which is our responsibility. (4) does not apply here.

### 8.3 Decision tree

On terminal failure:

```text
Is retry_count < 2?
|
+-- Yes:
|    Is failure class retriable?
|    (retriable = install failure, timeout, model error)
|    |
|    +-- Yes: increment retry_count, transition failed -> queued
|    |
|    +-- No:  transition failed -> escalated
|
+-- No (retry_count >= 2):
     transition failed -> escalated
     Notify human (Telegram, email, or GitHub issue comment)
     Write audit-log entry tagged as escalation
```

Failure classes:

| Class | Retriable | Action |
|---|---|---|
| Install failure (npm/pip) | Yes | Auto-retry. |
| VM timeout | Yes | Auto-retry. |
| Network error | Yes | Auto-retry (Jules will have tried first; this is our second layer). |
| Plan proposes out-of-scope edits | No | Escalate. Prompt needs a human rewrite. |
| Plan exceeds `max_files_changed` | No | Escalate. Scope was wrong. |
| CI fails after PR open | No | Escalate. Jules cannot self-diagnose CI failures reliably. |
| PR diff touches forbidden files | No | Escalate, and audit-log this as a governance event. |
| Model refuses task | No | Escalate. Prompt needs rewriting. |

### 8.4 Escalation output

Escalation produces three artifacts:

1. A comment on the Jules session in the web UI (manual; Zola checks the session).
2. A GitHub issue in `aigovclaw` tagged `jules-escalation`, with the `FlaggedIssue` ID, failure class, and session URL.
3. An audit-log entry (section 9).

## 9. Observability and audit

### 9.1 Governance requirement

AIGovClaw is a governance product. Every autonomous action must leave an audit trail per ISO 42001 Clause 9.1 (performance evaluation) and Clause 9.2 (internal audit). Jules sessions are autonomous actions. Therefore every Jules session produces an audit-log entry.

This is non-negotiable. A Jules session that does not produce an audit entry is a governance defect.

### 9.2 Audit loop

```text
Jules session terminal state reached (merged, rejected, escalated)
   |
   v
Dispatcher collects: session ID, session URL, FlaggedIssue ID, playbook,
  target repo, PR URL, final state, reviewer identity, timestamps
   |
   v
Dispatcher invokes audit-log-generator plugin with:
   event_type = "autonomous-agent-action"
   actor = "jules"
   playbook = <playbook name>
   outcome = merged | rejected | escalated
   iso_42001_clause = "9.1"
   linked_records = [FlaggedIssue ID, PR URL, Jules session URL]
   |
   v
audit-log-generator writes structured entry to ~/.hermes/memory/aigovclaw/audit/YYYY-MM.jsonl
   |
   v
Dispatcher updates FlaggedIssue record with audit_event_id
   |
   v
FlaggedIssue transitions to final state
```

Invariants:

- No `FlaggedIssue` reaches `merged` or `rejected` without an `audit_event_id` populated.
- The audit log is append-only. Corrections to past entries are new entries referencing the old entry, never mutations.
- Monthly, the human reviews the audit log. This review itself produces an audit entry (a Clause 9.2 internal audit record). This closes the loop.

### 9.3 Metrics

The dispatcher exposes counters that feed the `metrics-collector` plugin:

- Sessions dispatched per day, per playbook.
- Sessions merged vs rejected vs escalated.
- Mean time from `queued` to `merged`.
- Escalation rate per playbook.
- Terminal failure class distribution.

An escalation rate above 20 percent on any playbook for two consecutive weeks is a signal to retire or rewrite that playbook. The dispatcher emits this as an event; Zola reviews.

## 10. Cost and quota

### 10.1 Jules tier model

Published tiers:

| Tier  | Daily tasks | Concurrent | Model |
|-------|-------------|------------|-------|
| Free  | 15          | 3          | Gemini 2.5 Pro |
| Pro   | 100         | 15         | Priority on Gemini 3 Pro |
| Ultra | 300         | 60         | Priority on Gemini 3 Pro |

Daily counters are rolling 24 hours. When exhausted, the new-task button is disabled in the UI and API calls return quota errors.

### 10.2 AIGovOps budget estimate

Estimated sustained load for a steady-state AIGovOps catalogue at 12 plugins:

| Playbook | Dispatch frequency | Sessions per week |
|---|---|---|
| Framework drift | Event-driven, rare | 1 to 3 |
| Test coverage gap | Event-driven, bursty | 5 to 10 (then zero until new plugin) |
| Dependency bump | Weekly scheduled | 1 to 5 |
| Citation drift | Weekly scheduled | 0 to 2 |
| Markdown lint | Daily scheduled | 0 to 7 |
| New plugin scaffold | Event-driven, rare | 0 to 1 |
| Link and TOC | Daily scheduled | 0 to 7 |
| Prohibited-content sweep | Daily scheduled | 0 to 7 |

Conservative upper bound: roughly 40 sessions per week in steady state. Spike case (new plugin landing with coverage backfill): 60 sessions in one week.

### 10.3 Recommended tier

- **Free tier**: 15 tasks per day equals about 105 per week. Sufficient for steady state, tight on spikes, insufficient margin for scheduled plus event bursts on the same day. Max concurrency of 3 means a scheduled daily sweep alone can saturate if it fans out across repos.
- **Pro tier**: 100 per day, 15 concurrent. Clean margin for all projected workloads. Recommended for Phase 2 and beyond.
- **Ultra tier**: not justified.

Recommendation: start Phase 0 and Phase 1 on Free tier (dry run plus single-playbook trial stays under 15 per day). Move to Pro tier when Phase 2 fans out to multiple scheduled playbooks.

### 10.4 Cost controls

- `max_files_changed` cap per playbook prevents runaway PRs.
- Dispatcher enforces `MAX_PARALLEL_JULES_SESSIONS` (see open question 11.4). Default proposal: 2. This is below free-tier concurrency so the dispatcher never hits the Jules concurrency ceiling; that ceiling should only be hit by scheduled tasks from the web UI.
- Dispatcher enforces `MAX_SESSIONS_PER_DAY` per repo. Default proposal: 10. This is a dispatcher-side circuit breaker independent of Jules's quota.
- When circuit breakers trip, the dispatcher stops queuing and writes an audit-log entry.

## 11. Resolved decisions

The following decisions were open during draft and are now resolved. Each answer is load-bearing for dispatcher, workflow, and playbook implementation.

1. **Repo write access.** Jules has write access to both `ZOLAtheCodeX/aigovops` and `ZOLAtheCodeX/aigovclaw`, scoped to playbook-created branches only. No direct push to `main`. No protected-branch bypass. Every PR requires human review before merge, including auto-created ones.

2. **Auto-merge policy.** No playbook auto-merges in Phase 1 or Phase 2. All PRs require explicit human approval. Phase 3 may permit auto-merge for `dep-bump` (4.3) and `markdown-lint` (4.5) only if all three conditions hold: CI is fully green, the diff is under 20 lines, and the change is wholly contained to dependency-lockfile surface area or lint-surface area. Any diff that exceeds these bounds routes to human review regardless.

3. **MAX_PARALLEL_JULES_SESSIONS.** Hard cap: 3 in Phase 1, 5 in Phase 2, 10 in Phase 3. Enforced by the dispatcher at record-validation time. The GitHub Actions path enforces the same cap via the `concurrency:` keyword in each workflow file. If both paths dispatch concurrently, the dispatcher queries `gh run list` to count active GH Actions runs and subtracts from its own quota.

4. **Cost budget.** Phase 0 and Phase 1 run on Jules Free tier, quota-limited. Phase 2 moves to Pro tier at the team-billing boundary, triggered when sustained weekly volume justifies it. Alarm fires if any rolling 7-day window exceeds 80 percent of plan quota. Alarm routes per open item 8 below.

5. **Secrets rotation cadence.** Quarterly, or immediately on any suspected compromise. Rotation mechanics: update the GitHub Secret, reload the dispatcher environment. No code change required. Old key revoked after one successful dispatch confirms the new key.

6. **Target branch pattern.** `jules/<playbook>-<fi_id>`, where `<fi_id>` is the FlaggedIssue ID slug. Deterministic, human-readable, collision-proof. Branch is auto-deleted 7 days after PR merge (GitHub setting plus dispatcher fallback sweep).

7. **PR title pattern.** `[jules:<playbook>] <short-description>`. The short-description is generated by Jules. The dispatcher validates that the `[jules:<playbook>]` prefix is present and that `<playbook>` matches the FlaggedIssue record's `playbook` field. Mismatch triggers the `plan-out-of-scope` terminal failure class.

8. **Review queue destination.** Primary: GitHub PR review (one reviewer, Zola). Secondary: audit-log entry in `~/.hermes/memory/aigovclaw/audit/YYYY-MM.jsonl`, immutable, append-only. Escalations produce two additional outputs: a Telegram message to the Hermes bot on the zo-pi Raspberry Pi, and a new row on the AIGovOps Notion project page (ID `344a16ad15d48122aebed3a507cd9e7e`). The Telegram path is for low-latency attention; the Notion path is for calendar-week review.

9. **Draft vs ready-for-review PRs.** All Jules PRs open as draft. The dispatcher promotes a PR to ready-for-review only if both conditions hold: CI is green, and the originating FlaggedIssue carries `auto_ready_on_green: true` in its metadata. Default value is `false`. This keeps the reviewer's queue clean by default.

10. **Terminal failure classes.** The dispatcher recognizes seven classes: `install-failure`, `test-failure`, `timeout`, `model-error`, `api-quota-exceeded`, `plan-out-of-scope`, `repo-access-denied`. The first three are retriable up to 2 attempts. The last four are terminal on first occurrence and escalate immediately per section 8.

11. **Playbook stale-safety check.** Every playbook file MUST begin with a Step 0 stale-check preamble (added in a parallel commit). The preamble instructs Jules to verify its assumptions against the current repo state before proposing any edit. The dispatcher refuses to render a prompt from any playbook whose file does not start with the required preamble; this raises `PlaybookValidationError` and blocks dispatch.

12. **Observability and dashboards.** Phase 1: structured JSON logs to stderr, captured by the dispatcher host's log rotation. Phase 2: logs ship to the AIGovClaw hub and render as a static HTML dashboard. Phase 3: optional Grafana dashboard for teams running the hosted hub tier. Metrics specified in section 9.3 are emitted at all three phases; only the surface changes.

## 12. Non-goals

Explicit list of things this integration does not do. If scope creeps to include any of these, that is a governance failure, not a feature gap.

1. Jules does not author `SKILL.md` body content from scratch. All framework interpretation is human or Claude Code work.
2. Jules does not make framework-interpretation calls. Deciding what ISO 42001 Annex A.6.2.8 means in a given context is human work.
3. Jules does not touch production artifacts. A plugin-run output that has been promoted to client deliverable status is never edited by Jules, even for markdown lint.
4. Jules does not merge PRs. Every merge to `main` is human.
5. Jules does not bump package versions in release metadata or create tags.
6. Jules does not edit this design document, `AGENTS.md`, `SECURITY.md`, `LICENSE`, `persona/SOUL.md`, or the `tools:` security block of `config/hermes.yaml`. These are repo-policy forbidden.
7. Jules does not read or write `~/.hermes/memory/aigovclaw/`. The Hermes agent owns that path.
8. Jules does not operate on any repository outside `aigovops` and `aigovclaw`.
9. Jules does not replace Claude Code. The two coexist. Claude Code for design and feature work, Jules for maintenance.
10. Jules does not author the audit log. The `audit-log-generator` plugin, invoked by the dispatcher, writes audit entries. Jules's PR is the input event, not the log writer.

## 13. Phased rollout

### Phase 0: manual dry run, no API calls

Goal: validate that Jules respects `AGENTS.md` and the forbidden-file list on these specific repos before any automation exists.

Steps:

1. Merge this design doc after user approval.
2. Human opens a Jules session via web UI against `aigovops` with a trivial no-op prompt ("print the contents of AGENTS.md"). Verify activity feed shows Jules read the file.
3. Human opens a Jules session via web UI with a prompt that attempts to edit a forbidden file ("edit SECURITY.md to add a minor typo fix"). Verify Jules either refuses or produces a plan that the human can reject. This tests the policy honor.
4. Human opens one session per playbook entry manually, from the web UI, to validate the prompt quality before it is ever invoked via API.
5. Document findings in `jules/README.md`.

Exit criteria: all eight playbook prompts produce acceptable PRs (or acceptable refusals) when run manually. Any playbook that fails validation is redrafted before Phase 1.

Duration estimate: one evening per playbook, spread over two weeks.

### Phase 1: single playbook, API-dispatched, human approves every PR

Goal: validate the dispatcher against the smallest-surface playbook.

Selected playbook: 4.5 (markdown lint regression). It is mechanical, well-scoped, and low-risk.

Steps:

1. Implement dispatcher (separate PR, after this design is approved).
2. Implement schemas (separate PR).
3. Dispatch only 4.5 playbook. All other playbooks remain manual.
4. Every PR requires human review and merge. No auto-merge even though 4.5 is flagged auto-merge eligible. (Auto-merge comes in Phase 2 after trust is established.)
5. Run for four weeks minimum. Measure: dispatch latency, success rate, escalation rate, time-to-merge.

Exit criteria: escalation rate under 10 percent, zero governance incidents (no forbidden file touched), zero missing audit entries.

### Phase 2: multi-playbook, scheduled tasks enabled

Goal: fan out to the full playbook with scheduled tasks active.

Steps:

1. Enable playbooks 4.3, 4.4, 4.7, 4.8 on scheduled cadences per section 5.2.
2. Enable playbooks 4.1, 4.2 as event-triggered. Human or Claude Code flags issues.
3. Retain playbook 4.6 (new plugin scaffold) as human-initiated only.
4. Enable auto-merge only for 4.5 and 4.7 after they have run clean for four weeks under Phase 1 conditions.
5. Move to Pro tier if volume justifies.
6. Monthly audit-log review added to Zola's calendar.

Exit criteria: steady-state operation for six weeks with under 15 percent escalation rate overall.

### Phase 3: full autonomy with human approval gate only

Goal: Jules runs the maintenance surface end-to-end, human acts only as PR approver and monthly auditor.

State:

1. All eight playbook entries active.
2. Scheduled tasks running on their defined cadences.
3. Dispatcher handles retry and escalation automatically.
4. Human attention cost drops to: (a) PR review for non-auto-merge playbooks, (b) monthly audit-log review, (c) monthly scheduled-task registry review, (d) quarterly playbook review to prune or add entries.
5. Claude Code remains available for foreground feature work and for any incident response.

Exit criteria: this is the steady state. No exit.

## 14. GitHub Actions dispatch path

This section specifies the GH Actions path introduced in section 5. It is the primary dispatch mechanism for all playbooks except 4.6 (new plugin scaffold).

### 14.1 Workflow file naming

One workflow file per playbook per target repo:

```text
.github/workflows/jules-<playbook>.yml
```

Examples:

- `.github/workflows/jules-framework-drift.yml`
- `.github/workflows/jules-dep-bump.yml`
- `.github/workflows/jules-markdown-lint.yml`

The workflow filename is the identifier. The dispatcher resolves a FlaggedIssue's `playbook` field to this filename when it needs to query GH Actions state.

### 14.2 Required secrets

| Secret | Scope | Purpose |
|---|---|---|
| `JULES_API_KEY` | Repo secret (or org secret, if both repos live under the same owner) | Auth header for `jules-invoke@v1`. |
| `GITHUB_TOKEN` | Provided by Actions runtime | Default write-scoped token. Sufficient for branch creation and PR open. |

No other secrets are required on the GH Actions path. The dispatcher's GitHub token is separate and is not used inside workflows.

### 14.3 Standard usage pattern

`jules-invoke@v1` accepts these inputs (the ones we use):

- `prompt`: the rendered playbook prompt. Injected from the playbook file at `aigovclaw/jules/playbook/<playbook>.md` via a prior `actions/checkout` step plus a read step.
- `jules_api_key`: `${{ secrets.JULES_API_KEY }}`.
- `starting_branch`: `main` (or the configured default).
- `include_last_commit`: `true`.
- `include_commit_log`: `true` for playbooks that benefit from recent history context (framework-drift, citation-drift, prohibited-content-sweep); `false` for playbooks that must only see working tree state (scaffold, dep-bump).

The `automationMode` and `requirePlanApproval` fields are set by the action itself based on action inputs; we pass equivalent flags so that the GH Actions path produces the same Jules session shape as the Python dispatcher path.

### 14.4 Concurrency

Every workflow declares:

```yaml
concurrency:
  group: jules-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: false
```

The group scope ensures two cron ticks of the same playbook on the same branch cannot run concurrently. `cancel-in-progress: false` preserves in-flight sessions so Jules is not killed mid-PR.

### 14.5 State sync between FlaggedIssue and GH Actions

The dispatcher treats GH Actions-dispatched runs as first-class sessions in the FlaggedIssue state machine. Sync flow:

1. For GH Actions-originated playbooks, the workflow writes a FlaggedIssue record stub (state = `dispatched`) to a staging branch via the GitHub API, then triggers `jules-invoke@v1`.
2. The dispatcher polls `gh run list --workflow=jules-<playbook>.yml --limit 1 --json status,conclusion,databaseId,url` to detect the run and attach the run URL to the FlaggedIssue.
3. On terminal Actions state (`completed` with conclusion `success` or `failure`), the dispatcher advances the FlaggedIssue to `draft-pr` or `failed` per section 3.2.
4. The audit-log hook in section 9.2 fires on either terminal state, using the GH Actions run URL as one of the `linked_records`.

### 14.6 When to prefer GH Actions vs Python dispatcher

Decision rubric. Use GH Actions when all of the following hold:

- The trigger condition is a GitHub event (`push`, `workflow_run`, `issues.labeled`, `schedule`, `workflow_dispatch`).
- The dispatch scope is a single repo per run.
- No cross-repo coordination is required at dispatch time.
- The FlaggedIssue record can be synthesized from the event payload (no human-authored metadata required beyond what the event carries).

Use the Python dispatcher when any of the following hold:

- A human is the proximate author of the FlaggedIssue (4.6 new plugin scaffold).
- Cross-repo paired issues must be validated before dispatch (`AGENTS.md` Section 7).
- The dispatch originates from the Hermes agent reasoning loop, not from GitHub.
- The retry needs custom backoff that differs from the GH Actions default rerun.
- The FlaggedIssue requires `auto_ready_on_green: true` promotion logic that the dispatcher owns.

In all cases, the audit-log-generator runs regardless of dispatch path. The governance posture is path-independent.

## 15. Approval

This document is a proposal. Nothing is built until the user signs off. The specific decisions that need explicit approval before implementation begins:

1. Overall approach (Jules as background worker, Claude Code as foreground).
2. The role-split table in section 2.
3. The playbook entries in section 4, as a complete set.
4. The answers to all open questions in section 11.
5. Phase 0 can begin immediately upon approval of items 1 to 4 above. Phase 1 requires a separate dispatcher implementation PR.

End of design proposal.
