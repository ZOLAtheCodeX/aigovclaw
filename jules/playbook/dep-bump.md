# Playbook: dep-bump

## Trigger

A scheduled weekly scan or a security advisory has surfaced a patch or minor version bump for a pinned dependency. Major version bumps never use this playbook. The FlaggedIssue payload names the dependency, the current version, the target version, and the bump class (patch or minor).

## Prompt

You are running as an autonomous coding agent in an isolated VM. You have no conversation history. Read this prompt in full before acting.

Target repository: {{TARGET_REPO}}
Target branch to base work on: {{TARGET_BRANCH}}
Working branch you must create: {{BRANCH_NAME}}
Pull request title: {{PR_TITLE}}
Flagged issue id: {{ISSUE_ID}}
Playbook: {{PLAYBOOK}}

Mandatory reading before any edit:

1. AGENTS.md at the repo root. Obey every rule there.
2. STYLE.md at the repo root.
3. The dependency manifests in the repo: `package.json`, `package-lock.json`, `requirements.txt`, `pyproject.toml`, or equivalent.
4. The repo's CHANGELOG.md if one exists.

Payload (JSON):

```json
{{PAYLOAD_JSON}}
```

## Step 0: Stale-issue check (mandatory, blocking)

Before any code change:

1. Extract from the source issue or FlaggedIssue payload the dependency name and the exact current pinned version string the issue claims is present in `requirements.txt`, `plugins/*/requirements.txt`, `package.json`, `pyproject.toml`, or equivalent manifest.
2. Verify each marker still exists in the current HEAD of the target branch. Use `grep -n` with the exact string. Report each marker with file path and line number.
3. If ANY marker is absent in the current HEAD:
   a. Do not open a PR.
   b. Do not modify any file except to post comments or close the source task.
   c. Identify the commit SHA that most recently touched the relevant path: `git log -1 --pretty=format:"%H %s" -- <path>`.
   d. Source-disposition (pick the one that applies and execute it):
      - If the source is a GitHub issue (you were invoked via `jules-invoke@v1` on an `issues` event OR the payload names a GitHub issue number): run `gh issue close <issue-number> --comment "Stale: resolved by commit <sha>. The marker referenced in the issue is no longer present in HEAD. Closing per AIGovOps stale-issue Step 0 protocol. If the underlying concern recurs, open a fresh issue against current HEAD."` This is take-resolving-action eligible (reversible; a human can reopen). Record the close in the session transcript.
      - If the source is a Jules web UI scheduled task (recurring trigger): DO NOT attempt to edit the scheduled task (web UI only, not API-addressable). Emit a structured warning at the top of the session transcript: `SCHEDULED-TASK-STALE: the triggering scheduled task references markers no longer in HEAD. Delete this scheduled task manually at https://jules.google and recreate only if the concern is current.` Name the task id if the payload supplies it.
      - If the source is ad-hoc (manual dispatch via `gh workflow run`, direct API call, or similar): emit a short session-transcript note `AD-HOC-STALE: marker not in HEAD. No recurring source to close.` Do not act further.
   e. Regardless of source, write an audit-log entry via the AIGovOps audit-log-generator plugin: `event_type="jules-stale-rejection"`, include the playbook name, the resolving commit SHA, the source disposition taken, and the path searched. This fires the ISO 42001 Clause 9.1 audit trail for the stale-rejection decision itself.
   f. Return verdict "rejected-stale" with a short rationale naming the commit SHA (one-line summary; full detail is in the audit entry).
4. If ALL markers are present: proceed to Step 1 below.

Stale-check rationale: issues are authored against a point-in-time snapshot. Commits between issue creation and playbook execution may have resolved the problem. Silently re-fixing an already-resolved issue produces spurious PRs, duplicate test coverage, and unstable IDs.

Task:

1. Confirm the target version in the payload is a patch or minor bump from the currently pinned version. If it is a major bump, stop and do not open a PR; write the finding to your plan.
2. Update the manifest and lockfile to pin the target version. Do not bump any other dependency.
3. Run the full test and lint suite. If anything fails, stop and do not open a PR.
4. If a CHANGELOG.md exists, add a single line under the unreleased section naming the dependency and new version.
5. Open a pull request with the exact title above. In the PR body, state the old version, new version, and bump class.

## Expected output

A single pull request with exactly one dependency version bump. Diff touches only the manifest, the lockfile, and at most one CHANGELOG.md. No source file edits. CI green.

## Success criteria

1. Diff touches only `package.json`, `package-lock.json`, `requirements.txt`, `pyproject.toml`, CHANGELOG.md, or equivalent manifest files.
2. Exactly one dependency version changes.
3. CI passes on every job.
4. No source file edits.
5. PR body states old version, new version, and bump class explicitly.

## Citations required

1. Upstream release notes URL for the new version, if available.
