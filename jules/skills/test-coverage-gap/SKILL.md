---
name: test-coverage-gap
description: Add focused test cases to an AIGovOps plugin when a coverage scan has identified missing assertion categories below the minimum threshold.
version: 0.1.0
scope: maintainer-tooling
license: MIT
compatible_agents: [jules, claude-code, cursor, gemini-cli, antigravity]
---

# Skill: test-coverage-gap

## When to use this skill

An AIGovOps plugin has fewer than the minimum assertion categories for its type. The gap was identified either by a scheduled coverage scan or by human review. The FlaggedIssue payload names the plugin directory, the missing assertion categories, and the target coverage threshold.

## Stale-issue check (Step 0, mandatory)

Before any code change:

1. Extract from the source issue or FlaggedIssue payload the target plugin directory under `plugins/<name>/` and the current test count or missing assertion categories the issue asserts are present.
2. Verify each marker still exists in the current HEAD of the target branch. Use `grep -n` with the exact string. Report each marker with file path and line number.
3. If ANY marker is absent in the current HEAD:
   a. Do not open a PR.
   b. Do not modify any file except to post a comment.
   c. Return verdict "rejected-stale" with a short rationale naming the commit SHA that most recently touched the relevant path (use `git log -1 --pretty=format:"%H %s" -- <path>`).
4. If ALL markers are present: proceed to the Task below.

Stale-check rationale: issues are authored against a point-in-time snapshot. Commits between issue creation and playbook execution may have resolved the problem. Silently re-fixing an already-resolved issue produces spurious PRs, duplicate test coverage, and unstable IDs.

Automate Step 0 via `scripts/stale-check.sh <issue-title> <file> <marker> [<file> <marker> ...]`.

## Task

1. Read the plugin's SKILL.md and schema.json to understand the contract.
2. Read the existing tests. Identify the assertion categories already covered.
3. For each missing assertion category named in the payload, add a focused test case under `plugins/<name>/tests/`.
4. Do not modify plugin source, schema, or SKILL.md. Tests only.
5. Run the full test suite. If any existing test fails, stop and do not open a PR. See `scripts/post-check.sh`.
6. Open a pull request with the title pattern in `assets/pr-title.txt`.

## Success criteria

1. New tests exist under `plugins/<name>/tests/`.
2. All new tests pass locally.
3. All existing tests still pass.
4. Test names match the naming convention documented in CONTRIBUTING.md (or, if absent, the style used by sibling tests in the same directory).
5. No emoji, no em-dash, no hedging language in any test file docstring or comment.
6. No edits to files outside `plugins/<name>/tests/`.

## Scripts available

- `scripts/stale-check.sh` - Step 0 gate.
- `scripts/post-check.sh` - runs the repo test suite (pytest) after the edit. Exit non-zero means do not open the PR.

## Resources

- `assets/pr-title.txt`, `assets/branch-name.txt`, `assets/commit-message.txt` - naming and commit templates.
