# Playbook: link-toc

## Trigger

The scheduled nightly link checker has found broken internal anchors or the README table-of-contents is missing entries for sub-documents that exist in the repo. The FlaggedIssue payload lists the README, the broken anchors, or the missing sub-doc paths.

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
3. The README.md in question and every sub-document it references.

Payload (JSON):

```json
{{PAYLOAD_JSON}}
```

Task:

1. For each broken anchor, locate the target heading in the referenced file. Update the link text and anchor slug to match the current heading.
2. For each missing sub-doc, add an entry to the table of contents in the correct alphabetical or structural position (match existing TOC style).
3. Do not edit any prose outside the TOC block and the link tokens themselves. No heading rewrites, no added sections.
4. Run the link checker locally. All links must resolve.
5. Open a pull request with the exact title above. PR body must state "link-and-toc only."

## Expected output

A single pull request that fixes broken anchors and adds missing TOC entries. No content changes. No heading edits. No added sections.

## Success criteria

1. Link checker passes after the PR.
2. Diff is link-token and TOC-block changes only.
3. No heading edits.
4. No added or removed sections.
5. PR body states "link-and-toc only."

## Citations required

None.
