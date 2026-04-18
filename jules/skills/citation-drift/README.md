# citation-drift

Maintainer-scoped Agent Skill for rewriting repo citations to STYLE.md canonical format without semantic text changes.

## Purpose

A scheduled grep or human review has flagged citations that do not match STYLE.md. This skill drives an autonomous coding agent to rewrite the offending citation token in place, preserving all surrounding prose.

## Trigger conditions

- Scheduled citation-lint job finds a non-canonical citation.
- Human review flags a drift.
- FlaggedIssue payload lists files, line refs, and the preferred format.

## Install across agents

Maintainer-scoped; end-users of AIGovClaw do not invoke it.

- **Jules:** `npx skills add google-labs-code/jules-skills --skill citation-drift --global`.
- **Claude Code:** copy into `~/.claude/skills/citation-drift/` or use `jules/skills/install.sh --target claude-code`.
- **Cursor, Gemini CLI, Antigravity:** copy the directory into the agent's skills directory.

## Test locally

```bash
echo 'See ISO/IEC 42001, Clause 6.1.2 for details.' > drift.md
bash /path/to/jules/skills/citation-drift/scripts/post-check.sh drift.md
# Expect exit 1 with message about ':2023' missing.
```

## Resources

- `resources/citation-rules.md` - self-contained canonical citation formats for ISO 42001, NIST AI RMF, and EU AI Act. Mirrors aigovops STYLE.md.

## Source

Derived from `jules/playbook/citation-drift.md`.
