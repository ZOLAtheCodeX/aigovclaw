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

## Step 0: Stale-issue check (mandatory, blocking)

Before any code change:

1. Extract from the source issue or FlaggedIssue payload the README file path, the exact broken anchor strings, and the heading text or sub-document path the issue claims is missing from the TOC.
2. Verify each marker still exists in the current HEAD of the target branch. Use `grep -n` with the exact string. Report each marker with file path and line number.
3. If ANY marker is absent in the current HEAD:
   a. Do not open a PR.
   b. Do not modify any file except to post a comment.
   c. Return verdict "rejected-stale" with a short rationale naming the commit SHA that most recently touched the relevant path (use `git log -1 --pretty=format:"%H %s" -- <path>`).
4. If ALL markers are present: proceed to Step 1 below.

Stale-check rationale: issues are authored against a point-in-time snapshot. Commits between issue creation and playbook execution may have resolved the problem. Silently re-fixing an already-resolved issue produces spurious PRs, duplicate test coverage, and unstable IDs.

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
