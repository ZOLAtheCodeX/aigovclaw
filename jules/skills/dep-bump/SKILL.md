---
name: dep-bump
description: Apply a patch or minor dependency version bump surfaced by a weekly scan or a security advisory, with no other changes.
version: 0.1.0
scope: maintainer-tooling
license: MIT
compatible_agents: [jules, claude-code, cursor, gemini-cli, antigravity]
---

# Skill: dep-bump

## When to use this skill

A scheduled weekly scan or a security advisory has surfaced a patch or minor version bump for a pinned dependency. Major version bumps never use this skill. The FlaggedIssue payload names the dependency, the current version, the target version, and the bump class (patch or minor).

## Stale-issue check (Step 0, mandatory)

Before any code change:

1. Extract from the source issue or FlaggedIssue payload the dependency name and the exact current pinned version string the issue claims is present in `requirements.txt`, `plugins/*/requirements.txt`, `package.json`, `pyproject.toml`, or equivalent manifest.
2. Verify each marker still exists in the current HEAD of the target branch. Use `grep -n` with the exact string. Report each marker with file path and line number.
3. If ANY marker is absent in the current HEAD:
   a. Do not open a PR.
   b. Do not modify any file except to post a comment.
   c. Return verdict "rejected-stale" with a short rationale naming the commit SHA that most recently touched the relevant path (use `git log -1 --pretty=format:"%H %s" -- <path>`).
4. If ALL markers are present: proceed to the Task below.

Stale-check rationale: issues are authored against a point-in-time snapshot. Commits between issue creation and playbook execution may have resolved the problem. Silently re-fixing an already-resolved issue produces spurious PRs, duplicate test coverage, and unstable IDs.

Automate Step 0 via `scripts/stale-check.sh <issue-title> <manifest-file> <pinned-version-string>`.

## Task

1. Confirm the target version in the payload is a patch or minor bump from the currently pinned version. If it is a major bump, stop and do not open a PR; write the finding to your plan.
2. Update the manifest and lockfile to pin the target version. Do not bump any other dependency.
3. Run the full test and lint suite via `scripts/post-check.sh`. If anything fails, stop and do not open a PR.
4. If a CHANGELOG.md exists, add a single line under the unreleased section naming the dependency and new version.
5. Open a pull request with the title pattern in `assets/pr-title.txt`. In the PR body, state the old version, new version, and bump class.

## Success criteria

1. Diff touches only `package.json`, `package-lock.json`, `requirements.txt`, `pyproject.toml`, CHANGELOG.md, or equivalent manifest files.
2. Exactly one dependency version changes.
3. CI passes on every job.
4. No source file edits.
5. PR body states old version, new version, and bump class explicitly.

## Scripts available

- `scripts/stale-check.sh` - Step 0 gate.
- `scripts/post-check.sh` - runs the repo's test and lint suite (pytest, ruff, or npm test per manifest type). Exit non-zero means do not open the PR.

## Resources

- `assets/pr-title.txt`, `assets/branch-name.txt`, `assets/commit-message.txt` - naming and commit templates.
