# Playbook: test-coverage-gap

## Trigger

An AIGovOps plugin has fewer than the minimum assertion categories for its type. The gap was identified either by a scheduled coverage scan or by human review. The FlaggedIssue payload names the plugin directory, the missing assertion categories, and the target coverage threshold.

## Prompt

You are running as an autonomous coding agent in an isolated VM. You have no conversation history. Read this prompt in full before acting.

Target repository: {{TARGET_REPO}}
Target branch to base work on: {{TARGET_BRANCH}}
Working branch you must create: {{BRANCH_NAME}}
Pull request title: {{PR_TITLE}}
Flagged issue id: {{ISSUE_ID}}
Playbook: {{PLAYBOOK}}

Mandatory reading before any edit:

1. AGENTS.md at the repo root. Obey every rule there, especially Section 3 (forbidden files) and Section 1 (prose rules).
2. STYLE.md at the repo root.
3. CONTRIBUTING.md if it exists, for the test naming convention.
4. The plugin under test: `plugins/<name>/SKILL.md`, `plugins/<name>/schema.json`, and existing tests under `plugins/<name>/tests/`.

Payload (JSON):

```json
{{PAYLOAD_JSON}}
```

## Step 0: Stale-issue check (mandatory, blocking)

Before any code change:

1. Extract from the source issue or FlaggedIssue payload the target plugin directory under `plugins/<name>/` and the current test count or missing assertion categories the issue asserts are present.
2. Verify each marker still exists in the current HEAD of the target branch. Use `grep -n` with the exact string. Report each marker with file path and line number.
3. If ANY marker is absent in the current HEAD:
   a. Do not open a PR.
   b. Do not modify any file except to post a comment.
   c. Return verdict "rejected-stale" with a short rationale naming the commit SHA that most recently touched the relevant path (use `git log -1 --pretty=format:"%H %s" -- <path>`).
4. If ALL markers are present: proceed to Step 1 below.

Stale-check rationale: issues are authored against a point-in-time snapshot. Commits between issue creation and playbook execution may have resolved the problem. Silently re-fixing an already-resolved issue produces spurious PRs, duplicate test coverage, and unstable IDs.

Task:

1. Read the plugin's SKILL.md and schema.json to understand the contract.
2. Read the existing tests. Identify the assertion categories already covered.
3. For each missing assertion category named in the payload, add a focused test case under `plugins/<name>/tests/`.
4. Do not modify plugin source, schema, or SKILL.md. Tests only.
5. Run the full test suite. If any existing test fails, stop and do not open a PR.
6. Open a pull request with the exact title above.

## Expected output

A single pull request that adds new test cases under `plugins/<name>/tests/`. No changes to plugin source, schema, or SKILL.md. Every new test case matches the repo's naming convention and has a concise, non-hedging docstring.

## Success criteria

1. New tests exist under `plugins/<name>/tests/`.
2. All new tests pass locally.
3. All existing tests still pass.
4. Test names match the naming convention documented in CONTRIBUTING.md (or, if absent, the style used by sibling tests in the same directory).
5. No emoji, no em-dash, no hedging language in any test file docstring or comment.
6. No edits to files outside `plugins/<name>/tests/`.

## Citations required

None. This is mechanical test scaffolding. The plugin's own SKILL.md already carries the framework citations.
