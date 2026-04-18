# Playbook: citation-drift

## Trigger

A scheduled grep or human review has found a citation in the repo that does not match the canonical format in STYLE.md. The FlaggedIssue payload lists the file paths and line references where the drift was detected, and the preferred format.

## Prompt

You are running as an autonomous coding agent in an isolated VM. You have no conversation history. Read this prompt in full before acting.

Target repository: {{TARGET_REPO}}
Target branch to base work on: {{TARGET_BRANCH}}
Working branch you must create: {{BRANCH_NAME}}
Pull request title: {{PR_TITLE}}
Flagged issue id: {{ISSUE_ID}}
Playbook: {{PLAYBOOK}}

Mandatory reading before any edit:

1. STYLE.md at the repo root. This is the source of truth for citation format.
2. AGENTS.md at the repo root. Obey every rule there.

Payload (JSON):

```json
{{PAYLOAD_JSON}}
```

Task:

1. For each file path and line reference in the payload, rewrite the offending citation in place. Match STYLE.md examples exactly, character for character.
2. Do not change any prose outside the citation token itself. No paraphrasing, no reformatting surrounding sentences.
3. Do not add new sources. If a citation is malformed because a URL is broken, flag it in your plan and do not fix it in this PR.
4. Run link checks and lint. If anything fails, stop.
5. Open a pull request with the exact title above.

## Expected output

A single pull request that rewrites citations in place across the files listed in the payload. No semantic text changes. No new sources. Diff confined to citation tokens.

## Success criteria

1. Grep for the anti-pattern described in the payload returns zero matches after the PR.
2. Grep for the preferred pattern described in the payload returns at least as many matches as before the PR.
3. No semantic text changes outside the citation token itself.
4. No files edited outside those listed in the payload.
5. Link checker passes.

## Citations required

1. STYLE.md, by path, as the authoritative rule.
