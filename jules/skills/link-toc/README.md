# link-toc

Maintainer-scoped Agent Skill for fixing broken internal anchors and adding missing README table-of-contents entries.

## Purpose

The scheduled nightly link checker found broken anchors or a README TOC is missing entries for existing sub-documents. This skill drives an autonomous coding agent to repair link tokens and TOC entries only, with no heading or prose edits.

## Trigger conditions

- Nightly link checker fails on internal anchors.
- TOC drift scanner reports a sub-doc path present in the repo but absent in the README TOC.
- FlaggedIssue payload lists README path, broken anchors, missing sub-doc paths.

## Install across agents

Maintainer-scoped; end-users of AIGovClaw do not invoke it.

- **Jules:** `npx skills add google-labs-code/jules-skills --skill link-toc --global`.
- **Claude Code:** copy into `~/.claude/skills/link-toc/` or use `jules/skills/install.sh --target claude-code`.
- **Cursor, Gemini CLI, Antigravity:** copy the directory into the agent's skills directory.

## Test locally

```bash
npm install -g markdown-link-check
bash /path/to/jules/skills/link-toc/scripts/post-check.sh README.md
```

## Source

Derived from `jules/playbook/link-toc.md`.
