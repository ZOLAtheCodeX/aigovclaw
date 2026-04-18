---
name: link-toc
description: Fix broken internal anchors and add missing README table-of-contents entries, without prose or heading edits.
version: 0.1.0
scope: maintainer-tooling
license: MIT
compatible_agents: [jules, claude-code, cursor, gemini-cli, antigravity]
---

# Skill: link-toc

## When to use this skill

The scheduled nightly link checker has found broken internal anchors or the README table-of-contents is missing entries for sub-documents that exist in the repo. The FlaggedIssue payload lists the README, the broken anchors, or the missing sub-doc paths.

## Stale-issue check (Step 0, mandatory)

Before any code change:

1. Extract from the source issue or FlaggedIssue payload the README file path, the exact broken anchor strings, and the heading text or sub-document path the issue claims is missing from the TOC.
2. Verify each marker still exists in the current HEAD of the target branch. Use `grep -n` with the exact string. Report each marker with file path and line number.
3. If ANY marker is absent in the current HEAD:
   a. Do not open a PR.
   b. Do not modify any file except to post a comment.
   c. Return verdict "rejected-stale" with a short rationale naming the commit SHA that most recently touched the relevant path (use `git log -1 --pretty=format:"%H %s" -- <path>`).
4. If ALL markers are present: proceed to the Task below.

Stale-check rationale: issues are authored against a point-in-time snapshot. Commits between issue creation and playbook execution may have resolved the problem. Silently re-fixing an already-resolved issue produces spurious PRs, duplicate test coverage, and unstable IDs.

Automate Step 0 via `scripts/stale-check.sh <issue-title> <readme> <anchor> [<readme> <anchor> ...]`.

## Task

1. For each broken anchor, locate the target heading in the referenced file. Update the link text and anchor slug to match the current heading.
2. For each missing sub-doc, add an entry to the table of contents in the correct alphabetical or structural position (match existing TOC style).
3. Do not edit any prose outside the TOC block and the link tokens themselves. No heading rewrites, no added sections.
4. Run the link checker locally via `scripts/post-check.sh`. All links must resolve.
5. Open a pull request with the title pattern in `assets/pr-title.txt`. PR body must state "link-and-toc only."

## Success criteria

1. Link checker passes after the PR.
2. Diff is link-token and TOC-block changes only.
3. No heading edits.
4. No added or removed sections.
5. PR body states "link-and-toc only."

## Scripts available

- `scripts/stale-check.sh` - Step 0 gate.
- `scripts/post-check.sh` - runs a link checker (markdown-link-check) over the README and its referenced files.

## Resources

- `assets/pr-title.txt`, `assets/branch-name.txt`, `assets/commit-message.txt` - naming and commit templates.
