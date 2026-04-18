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
