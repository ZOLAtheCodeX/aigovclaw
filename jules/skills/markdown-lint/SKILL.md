---
name: markdown-lint
description: Fix markdown lint violations (whitespace, heading level, list markers, line length, code fence language) without prose edits.
version: 0.1.0
scope: maintainer-tooling
license: MIT
compatible_agents: [jules, claude-code, cursor, gemini-cli, antigravity]
---

# Skill: markdown-lint

## When to use this skill

The markdown lint job on main has failed, or the scheduled nightly lint sweep has flagged warnings. The FlaggedIssue payload lists the offending files and lint rule IDs.

## Stale-issue check (Step 0, mandatory)

Before any code change:

1. Extract from the source issue or FlaggedIssue payload the specific file path, line number, and lint rule ID the issue claims is currently failing.
2. Verify each marker still exists in the current HEAD of the target branch. Use `grep -n` with the exact string. Report each marker with file path and line number.
3. If ANY marker is absent in the current HEAD:
   a. Do not open a PR.
   b. Do not modify any file except to post comments or close the source task.
   c. Identify the commit SHA that most recently touched the relevant path: `git log -1 --pretty=format:"%H %s" -- <path>`.
   d. Source-disposition (pick the one that applies and execute it):
      - If the source is a GitHub issue (you were invoked via `jules-invoke@v1` on an `issues` event OR the payload names a GitHub issue number): run `gh issue close <issue-number> --comment "Stale: resolved by commit <sha>. The marker referenced in the issue is no longer present in HEAD. Closing per AIGovOps stale-issue Step 0 protocol. If the underlying concern recurs, open a fresh issue against current HEAD."` This is take-resolving-action eligible (reversible; a human can reopen). Record the close in the session transcript.
      - If the source is a Jules web UI scheduled task (recurring trigger): DO NOT attempt to edit the scheduled task (web UI only, not API-addressable). Emit a structured warning at the top of the session transcript: `SCHEDULED-TASK-STALE: the triggering scheduled task references markers no longer in HEAD. Delete this scheduled task manually at https://jules.google and recreate only if the concern is current.` Name the task id if the payload supplies it.
      - If the source is ad-hoc (manual dispatch via `gh workflow run`, direct API call, or similar): emit a short session-transcript note `AD-HOC-STALE: marker not in HEAD. No recurring source to close.` Do not act further.
   e. Regardless of source, write an audit-log entry via the AIGovOps audit-log-generator plugin: `event_type="jules-stale-rejection"`, include the skill name, the resolving commit SHA, the source disposition taken, and the path searched. This fires the ISO 42001 Clause 9.1 audit trail for the stale-rejection decision itself.
   f. Return verdict "rejected-stale" with a short rationale naming the commit SHA (one-line summary; full detail is in the audit entry).
4. If ALL markers are present: proceed to the Task below.

Stale-check rationale: issues are authored against a point-in-time snapshot. Commits between issue creation and playbook execution may have resolved the problem. Silently re-fixing an already-resolved issue produces spurious PRs, duplicate test coverage, and unstable IDs.

Automate Step 0 via `scripts/stale-check.sh <issue-title> <file> <rule-id> [<file> <rule-id> ...]`.

## Task

1. For each file named in the payload, fix the lint violations named by rule ID. Whitespace, heading level, list marker, line length, and code fence language are the only categories permitted.
2. Do not edit any prose. Do not change word choice, sentence structure, or paragraph order. If a fix requires paragraph-level text edits, stop and do not open a PR.
3. Run the lint job locally via `scripts/post-check.sh`. All rules must pass before you open a PR.
4. Open a pull request with the title pattern in `assets/pr-title.txt`. Body must state "lint-only, no content changes."

## Success criteria

1. Lint job passes after the PR on every file.
2. Diff is whitespace, heading level, list marker, line length, or code fence language only.
3. No paragraph-level text edits.
4. PR body states "lint-only, no content changes."

## Scripts available

- `scripts/stale-check.sh` - Step 0 gate.
- `scripts/post-check.sh` - runs markdownlint-cli2 (falls back to markdownlint) against the configured `.markdownlint.json`. Exit 0 means clean.

## Resources

- `assets/pr-title.txt`, `assets/branch-name.txt`, `assets/commit-message.txt` - naming and commit templates.
