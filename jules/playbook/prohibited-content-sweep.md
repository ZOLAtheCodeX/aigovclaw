# Playbook: prohibited-content-sweep

## Trigger

A scheduled nightly grep has found an em-dash (U+2014), an emoji, or a hedging phrase in a repo file. AGENTS.md Section 1 forbids these. The FlaggedIssue payload lists the file paths, the anti-patterns found, and the substring matches.

## Prompt

You are running as an autonomous coding agent in an isolated VM. You have no conversation history. Read this prompt in full before acting.

Target repository: {{TARGET_REPO}}
Target branch to base work on: {{TARGET_BRANCH}}
Working branch you must create: {{BRANCH_NAME}}
Pull request title: {{PR_TITLE}}
Flagged issue id: {{ISSUE_ID}}
Playbook: {{PLAYBOOK}}

Mandatory reading before any edit:

1. AGENTS.md at the repo root. Section 1 lists every prohibited pattern. Obey it.
2. STYLE.md at the repo root.

Payload (JSON):

```json
{{PAYLOAD_JSON}}
```

Task:

1. For each em-dash, replace it with a hyphen ("-") or, where a hyphen would change meaning, a sentence split. Preserve meaning.
2. For each emoji, delete the character. If its removal makes the sentence ungrammatical, restructure the minimal adjacent words to restore grammar.
3. For each hedging phrase ("might", "perhaps", "could potentially", "arguably", "maybe", "it seems", "likely"), rewrite the sentence to a direct assertion. If the original author needed the hedge because the claim was genuinely uncertain, replace with a concrete confidence statement ("confidence: low", "confidence: medium") rather than deleting the hedge outright.
4. Do not change the technical meaning of any sentence.
5. Run the full test and lint suite. If anything fails, stop.
6. Open a pull request with the exact title above. PR body must list, for each file, the count of each anti-pattern fixed.

## Expected output

A single pull request that removes or replaces every prohibited-content match listed in the payload. No net content loss. Meaning preserved.

## Success criteria

1. Grep for em-dash returns zero matches in the files listed.
2. Grep for non-ASCII characters in `.md` files returns zero matches, except in files explicitly marked as allowed (if any).
3. Grep for the listed hedging phrases returns zero matches.
4. No sentence has become ungrammatical.
5. No net content loss (every edited sentence still makes its original technical point).
6. PR body lists per-file counts of each anti-pattern fixed.

## Citations required

1. AGENTS.md Section 1, by path, as the rule that forbids the patterns.
