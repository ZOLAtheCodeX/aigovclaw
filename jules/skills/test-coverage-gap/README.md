# test-coverage-gap

Maintainer-scoped Agent Skill for adding focused test cases to an AIGovOps plugin when a coverage scan has identified missing assertion categories.

## Purpose

An AIGovOps plugin is below the minimum assertion-category threshold for its type. This skill drives an autonomous coding agent to add focused tests under `plugins/<name>/tests/` without touching plugin source, schema, or SKILL.md.

## Trigger conditions

- Scheduled coverage scan flags a plugin below the threshold.
- Human review identifies a missing category.
- FlaggedIssue payload names the plugin directory, missing categories, and target threshold.

## Install across agents

This skill is maintainer-scoped; end-users of AIGovClaw do not invoke it.

- **Jules:** `npx skills add google-labs-code/jules-skills --skill test-coverage-gap --global`.
- **Claude Code:** copy into `~/.claude/skills/test-coverage-gap/` or use `jules/skills/install.sh --target claude-code`.
- **Cursor, Gemini CLI, Antigravity:** copy the directory into the agent's skills directory.

## Test locally

```bash
bash /path/to/jules/skills/test-coverage-gap/scripts/stale-check.sh "test" ./SKILL.md "marker"
bash /path/to/jules/skills/test-coverage-gap/scripts/post-check.sh
```

`post-check.sh` runs pytest (or npm test) from the current directory.

## Source

Derived from `jules/playbook/test-coverage-gap.md`.
