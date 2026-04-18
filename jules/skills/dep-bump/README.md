# dep-bump

Maintainer-scoped Agent Skill for applying a patch or minor dependency version bump, with no other changes.

## Purpose

A weekly scan or security advisory has surfaced a patch/minor version bump. This skill drives an autonomous coding agent to update manifest and lockfile, run tests and lint, and open a pull request. Major bumps are out of scope.

## Trigger conditions

- Scheduled weekly scan finds a patch/minor available.
- Security advisory identifies a pinned dependency needing update.
- FlaggedIssue payload names dependency, current version, target version, and bump class.

## Install across agents

Maintainer-scoped; end-users of AIGovClaw do not invoke it.

- **Jules:** `npx skills add google-labs-code/jules-skills --skill dep-bump --global`.
- **Claude Code:** copy into `~/.claude/skills/dep-bump/` or use `jules/skills/install.sh --target claude-code`.
- **Cursor, Gemini CLI, Antigravity:** copy the directory into the agent's skills directory.

## Test locally

```bash
bash /path/to/jules/skills/dep-bump/scripts/stale-check.sh "test" requirements.txt "requests==2.31.0"
bash /path/to/jules/skills/dep-bump/scripts/post-check.sh
```

`post-check.sh` runs pytest, ruff, and npm scripts if present.

## Source

Derived from `jules/playbook/dep-bump.md`.
