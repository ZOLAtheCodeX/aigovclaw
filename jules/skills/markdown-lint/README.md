# markdown-lint

Maintainer-scoped Agent Skill for fixing markdown lint violations without prose edits.

## Purpose

The markdown lint job has failed or the nightly lint sweep flagged warnings. This skill drives an autonomous coding agent to fix whitespace, heading level, list marker, line length, or code fence language violations only. Paragraph-level text edits are out of scope.

## Trigger conditions

- CI markdown lint job on main fails.
- Nightly lint sweep flags warnings.
- FlaggedIssue payload lists files and lint rule IDs.

## Install across agents

Maintainer-scoped; end-users of AIGovClaw do not invoke it.

- **Jules:** `npx skills add google-labs-code/jules-skills --skill markdown-lint --global`.
- **Claude Code:** copy into `~/.claude/skills/markdown-lint/` or use `jules/skills/install.sh --target claude-code`.
- **Cursor, Gemini CLI, Antigravity:** copy the directory into the agent's skills directory.

## Test locally

```bash
npm install -g markdownlint-cli2
bash /path/to/jules/skills/markdown-lint/scripts/post-check.sh
```

## Source

Derived from `jules/playbook/markdown-lint.md`.
