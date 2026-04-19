---
name: citation-drift
description: Rewrite repo citations in place when they do not match the canonical STYLE.md format, without semantic text changes.
version: 0.1.0
scope: maintainer-tooling
license: MIT
compatible_agents: [jules, claude-code, cursor, gemini-cli, antigravity]
---

# Skill: citation-drift

## When to use this skill

A scheduled grep or human review has found a citation in the repo that does not match the canonical format in STYLE.md. The FlaggedIssue payload lists the file paths and line references where the drift was detected, and the preferred format.

## Stale-issue check (Step 0, mandatory)

Before any code change:

1. Extract from the source issue or FlaggedIssue payload the specific verbatim citation strings the issue claims are malformed, along with their file paths and line references.
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

Automate Step 0 via `scripts/stale-check.sh <issue-title> <file> <citation-string> [<file> <citation-string> ...]`.

## Task

1. For each file path and line reference in the payload, rewrite the offending citation in place. Match the rules in `resources/citation-rules.md` exactly, character for character.
2. Do not change any prose outside the citation token itself. No paraphrasing, no reformatting surrounding sentences.
3. Do not add new sources. If a citation is malformed because a URL is broken, flag it in your plan and do not fix it in this PR.
4. Run link checks and lint via `scripts/post-check.sh`. If anything fails, stop.
5. Open a pull request with the title pattern in `assets/pr-title.txt`.

## Success criteria

1. Grep for the anti-pattern described in the payload returns zero matches after the PR.
2. Grep for the preferred pattern described in the payload returns at least as many matches as before the PR.
3. No semantic text changes outside the citation token itself.
4. No files edited outside those listed in the payload.
5. Link checker passes.

## Scripts available

- `scripts/stale-check.sh` - Step 0 gate.
- `scripts/post-check.sh` - greps for STYLE.md-noncompliant citations. Exit 0 means no drift remains; exit 1 names the offending file and line.

## Resources

- `resources/citation-rules.md` - self-contained canonical citation formats for ISO/IEC 42001:2023, NIST AI RMF 1.0, and the EU AI Act. Source of truth: aigovops STYLE.md.
- `assets/pr-title.txt`, `assets/branch-name.txt`, `assets/commit-message.txt` - naming and commit templates.
