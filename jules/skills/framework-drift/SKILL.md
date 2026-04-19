---
name: framework-drift
description: Correct text in an AIGovOps plugin SKILL.md when a framework-monitor process has detected drift from an authoritative source (ISO 42001, NIST AI RMF, or EU AI Act).
version: 0.1.0
scope: maintainer-tooling
license: MIT
compatible_agents: [jules, claude-code, cursor, gemini-cli, antigravity]
---

# Skill: framework-drift

## When to use this skill

A framework-monitor process or a human has detected drift between an authoritative source (ISO 42001, NIST AI RMF, or EU AI Act) and the text in an AIGovOps plugin SKILL.md. The FlaggedIssue payload includes the authoritative source URL, the affected file paths, and the specific paragraphs to correct.

## Stale-issue check (Step 0, mandatory)

Before any code change:

1. Extract from the source issue or FlaggedIssue payload the specific authoritative-source URL changes flagged by framework-monitor, the affected SKILL.md file path or paths, and the paragraph-identifying strings the issue claims still require correction.
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

Automate Step 0 via `scripts/stale-check.sh <issue-title> <file> <marker> [<file> <marker> ...]`. Exit code 1 means rejected-stale.

## Task

1. Fetch the authoritative source URL in the payload and identify the text that supersedes the current SKILL.md paragraphs.
2. Edit only the paragraphs named in the payload. Do not rewrite structure, do not add new sections, do not re-interpret the framework.
3. Update citations to match STYLE.md exactly. Cite by clause number, date accessed, and canonical URL. See `resources/citation-rules.md` in the sibling `citation-drift` skill for the canonical formats.
4. Run the repo's test suite if one exists. If tests fail, do not open a PR; write the failure to your plan and stop.
5. Open a pull request with the title pattern in `assets/pr-title.txt`. In the PR body, cite the authoritative source and list every paragraph changed.

## Success criteria

1. Diff touches only files in `target_paths`.
2. Total diff line count under `max_files_changed * 40` where `max_files_changed` is in the payload.
3. CI passes on every job.
4. Grep for em-dash (U+2014) in the PR diff returns zero matches.
5. Grep for emoji (non-ASCII in .md files) in the PR diff returns zero matches.
6. Grep for hedging words ("might", "perhaps", "could potentially", "arguably", "maybe") returns zero matches.
7. Every edited paragraph has a citation that matches the STYLE.md format exactly.
8. The PR body cites the authoritative source URL.

## Scripts available

- `scripts/stale-check.sh` - Step 0 gate. Verifies all markers named in the payload still exist at HEAD. Exits 0 if all present, 1 if any absent.

## Resources

- `assets/pr-title.txt` - PR title pattern.
- `assets/branch-name.txt` - branch naming pattern.
- `assets/commit-message.txt` - commit message template.
