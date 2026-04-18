# Playbook: framework-drift

## Trigger

A framework-monitor process or a human has detected drift between an authoritative source (ISO 42001, NIST AI RMF, or EU AI Act) and the text in an AIGovOps plugin SKILL.md. The FlaggedIssue payload includes the authoritative source URL, the affected file paths, and the specific paragraphs to correct.

## Prompt

You are running as an autonomous coding agent in an isolated VM. You have no conversation history. Read this prompt in full before acting.

Target repository: {{TARGET_REPO}}
Target branch to base work on: {{TARGET_BRANCH}}
Working branch you must create: {{BRANCH_NAME}}
Pull request title: {{PR_TITLE}}
Flagged issue id: {{ISSUE_ID}}
Playbook: {{PLAYBOOK}}

Mandatory reading before any edit:

1. AGENTS.md at the repo root. Obey every rule there. Section 3 lists files you must not touch under any circumstance. Section 1 bans em-dashes, emojis, and hedging language.
2. STYLE.md at the repo root. Follow every citation and prose rule.
3. The target SKILL.md file or files listed in the payload.

Payload (JSON):

```json
{{PAYLOAD_JSON}}
```

Task:

1. Fetch the authoritative source URL in the payload and identify the text that supersedes the current SKILL.md paragraphs.
2. Edit only the paragraphs named in the payload. Do not rewrite structure, do not add new sections, do not re-interpret the framework.
3. Update citations to match STYLE.md exactly. Cite by clause number, date accessed, and canonical URL.
4. Run the repo's test suite if one exists. If tests fail, do not open a PR; write the failure to your plan and stop.
5. Open a pull request with title exactly as given above. In the PR body, cite the authoritative source and list every paragraph changed.

## Expected output

A single pull request against {{TARGET_REPO}}:{{TARGET_BRANCH}} from {{BRANCH_NAME}} that edits only the files listed in the payload's `target_paths`. Diff size under 40 lines per file. No structural rewrites. No new sections. Citations updated to match STYLE.md.

## Success criteria

1. Diff touches only files in `target_paths`.
2. Total diff line count under `max_files_changed * 40` where `max_files_changed` is in the payload.
3. CI passes on every job.
4. Grep for em-dash (U+2014) in the PR diff returns zero matches.
5. Grep for emoji (non-ASCII in .md files) in the PR diff returns zero matches.
6. Grep for hedging words ("might", "perhaps", "could potentially", "arguably", "maybe") returns zero matches.
7. Every edited paragraph has a citation that matches the STYLE.md format exactly.
8. The PR body cites the authoritative source URL.

## Citations required

1. Authoritative source URL provided in the payload. Cite by section or clause number.
2. STYLE.md, by path, for the citation format used.
3. AGENTS.md Section 1 for the prose rules that the diff respects.
