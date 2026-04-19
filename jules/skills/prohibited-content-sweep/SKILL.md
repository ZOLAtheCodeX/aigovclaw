---
name: prohibited-content-sweep
description: Replace em-dashes, emojis, and hedging phrases flagged by the nightly grep sweep per AGENTS.md Section 1, preserving meaning.
version: 0.1.0
scope: maintainer-tooling
license: MIT
compatible_agents: [jules, claude-code, cursor, gemini-cli, antigravity]
---

# Skill: prohibited-content-sweep

## When to use this skill

A scheduled nightly grep has found an em-dash (U+2014), a banned glyph, or a hedging phrase in a repo file. AGENTS.md Section 1 forbids these. The FlaggedIssue payload lists the file paths, the anti-patterns found, and the substring matches.

## Stale-issue check (Step 0, mandatory)

Before any code change:

1. Extract from the source issue or FlaggedIssue payload the specific prohibited substring matches the issue lists: every em-dash (U+2014) occurrence by file and line, and every hedging-phrase hit sourced from the curated list in `tests/audit/consistency_audit.py`.
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

Automate Step 0 via `scripts/stale-check.sh <issue-title> <file> <substring> [<file> <substring> ...]`.

## Task

1. For each em-dash, replace it with a hyphen ("-") or, where a hyphen would change meaning, a sentence split. Preserve meaning.
2. For each banned glyph listed in `resources/prohibited-content.md`, delete the character. If its removal makes the sentence ungrammatical, restructure the minimal adjacent words to restore grammar.
3. For each hedging phrase in `resources/prohibited-content.md`, rewrite the sentence to a direct assertion. If the original author needed the hedge because the claim was genuinely uncertain, replace with a concrete confidence statement ("confidence: low", "confidence: medium") rather than deleting the hedge outright.
4. Do not change the technical meaning of any sentence.
5. Run the full test and lint suite via `scripts/post-check.sh`. If anything fails, stop.
6. Open a pull request with the title pattern in `assets/pr-title.txt`. PR body must list, for each file, the count of each anti-pattern fixed.

## Success criteria

1. Grep for em-dash returns zero matches in the files listed.
2. Grep for non-ASCII characters in `.md` files returns zero matches, except in files explicitly marked as allowed (if any).
3. Grep for the listed hedging phrases returns zero matches.
4. No sentence has become ungrammatical.
5. No net content loss (every edited sentence still makes its original technical point).
6. PR body lists per-file counts of each anti-pattern fixed.

## Scripts available

- `scripts/stale-check.sh` - Step 0 gate.
- `scripts/post-check.sh` - greps the modified files for em-dashes, non-ASCII in `.md`, and hedging phrases from `resources/prohibited-content.md`. Exit 0 means clean.

## Resources

- `resources/prohibited-content.md` - self-contained list of banned glyphs and hedging phrases extracted from aigovops `tests/audit/consistency_audit.py`.
- `assets/pr-title.txt`, `assets/branch-name.txt`, `assets/commit-message.txt` - naming and commit templates.
