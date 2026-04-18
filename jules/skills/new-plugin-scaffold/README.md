# new-plugin-scaffold

Maintainer-scoped Agent Skill for scaffolding a new AIGovOps plugin directory with no framework interpretation.

## Purpose

A human or Claude Code has designed a new plugin contract. This skill drives an autonomous coding agent to create `plugins/<name>/` with the required directory layout, an empty SKILL.md containing only section headers and TODO markers, a stub `schema.json`, and a pending placeholder test.

## Trigger conditions

- Contract for a new plugin is designed and approved.
- FlaggedIssue payload names the plugin name, artifact type, and skeleton constraints.
- Target directory MUST NOT exist at HEAD (inverted stale-check).

## Install across agents

Maintainer-scoped; end-users of AIGovClaw do not invoke it.

- **Jules:** `npx skills add google-labs-code/jules-skills --skill new-plugin-scaffold --global`.
- **Claude Code:** copy into `~/.claude/skills/new-plugin-scaffold/` or use `jules/skills/install.sh --target claude-code`.
- **Cursor, Gemini CLI, Antigravity:** copy the directory into the agent's skills directory.

## Test locally

```bash
bash /path/to/jules/skills/new-plugin-scaffold/scripts/post-check.sh
```

Runs pytest, ruff, markdownlint-cli2 if installed.

## Source

Derived from `jules/playbook/new-plugin-scaffold.md`.
