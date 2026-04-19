---
name: new-plugin-scaffold
description: Create an empty plugin directory skeleton (SKILL.md stub, schema.json stub, tests/ placeholder) for a newly-designed plugin contract, with no framework interpretation.
version: 0.1.0
scope: maintainer-tooling
license: MIT
compatible_agents: [jules, claude-code, cursor, gemini-cli, antigravity]
---

# Skill: new-plugin-scaffold

## When to use this skill

A human or Claude Code has designed a new plugin contract and flagged a scaffold request. The FlaggedIssue payload names the plugin name, the artifact type, and any skeleton constraints from the contract.

## Stale-issue check (Step 0, mandatory)

Before any code change:

1. Extract from the source issue or FlaggedIssue payload the target skill name, target artifact type, and the target plugin directory path under `plugins/<name>/` that MUST NOT already exist. For this skill the stale-check inverts: verify the target directory is absent at HEAD. If it is already present, the issue is stale.
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

Note: the inverted check requires verifying the directory is absent. The shared `scripts/stale-check.sh` helper checks marker strings. For this skill, the caller passes a reference-marker from `plugins/README.md` to confirm the contract is unchanged.

## Task

1. Create `plugins/<name>/` with the directory layout defined in `plugins/README.md`.
2. Create an empty SKILL.md containing only the section headers required by `plugins/README.md` and a single `TODO` marker in each body. Do not fill in any framework interpretation.
3. Create a stub `schema.json` that validates against the plugin-schema meta-schema. Empty properties object is acceptable.
4. Create a `tests/` directory with one placeholder test marked as skipped or pending.
5. If a plugin index exists, add an entry for the new plugin with no descriptive text beyond name and artifact type.
6. Run the repo's lint and test suite via `scripts/post-check.sh`. If anything fails, stop.
7. Open a pull request with the title pattern in `assets/pr-title.txt`. PR body must state "scaffold-only, no body content."

## Success criteria

1. Directory structure matches `plugins/README.md` exactly.
2. `schema.json` validates against the plugin-schema meta-schema.
3. Placeholder test is marked skipped or pending.
4. SKILL.md contains only section headers and TODO markers. No body content.
5. No framework interpretation, no control mappings, no risk taxonomy entries.
6. Existing tests still pass.

## Scripts available

- `scripts/stale-check.sh` - Step 0 gate.
- `scripts/post-check.sh` - runs the repo's lint and test suite after the scaffold is created.

## Resources

- `assets/pr-title.txt`, `assets/branch-name.txt`, `assets/commit-message.txt` - naming and commit templates.
