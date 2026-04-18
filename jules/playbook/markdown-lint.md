# Playbook: markdown-lint

## Trigger

The markdown lint job on main has failed, or the scheduled nightly lint sweep has flagged warnings. The FlaggedIssue payload lists the offending files and lint rule IDs.

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
2. `.markdownlint.json` at the repo root. This is the authoritative lint config.

Payload (JSON):

```json
{{PAYLOAD_JSON}}
```

## Step 0: Stale-issue check (mandatory, blocking)

Before any code change:

1. Extract from the source issue or FlaggedIssue payload the specific file path, line number, and lint rule ID the issue claims is currently failing.
2. Verify each marker still exists in the current HEAD of the target branch. Use `grep -n` with the exact string. Report each marker with file path and line number.
3. If ANY marker is absent in the current HEAD:
   a. Do not open a PR.
   b. Do not modify any file except to post a comment.
   c. Return verdict "rejected-stale" with a short rationale naming the commit SHA that most recently touched the relevant path (use `git log -1 --pretty=format:"%H %s" -- <path>`).
4. If ALL markers are present: proceed to Step 1 below.

Stale-check rationale: issues are authored against a point-in-time snapshot. Commits between issue creation and playbook execution may have resolved the problem. Silently re-fixing an already-resolved issue produces spurious PRs, duplicate test coverage, and unstable IDs.

Task:

1. For each file named in the payload, fix the lint violations named by rule ID. Whitespace, heading level, list marker, line length, and code fence language are the only categories permitted.
2. Do not edit any prose. Do not change word choice, sentence structure, or paragraph order. If a fix requires paragraph-level text edits, stop and do not open a PR.
3. Run the lint job locally. All rules must pass before you open a PR.
4. Open a pull request with the exact title above. Body must state "lint-only, no content changes."

## Expected output

A single pull request with whitespace, heading level, list marker, line length, or code fence language changes only. No paragraph-level text edits.

## Success criteria

1. Lint job passes after the PR on every file.
2. Diff is whitespace, heading level, list marker, line length, or code fence language only.
3. No paragraph-level text edits.
4. PR body states "lint-only, no content changes."

## Citations required

None. This is mechanical formatting.
