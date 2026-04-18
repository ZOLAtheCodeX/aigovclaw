# prohibited-content-sweep

Maintainer-scoped Agent Skill for replacing em-dashes, banned glyphs, and hedging phrases flagged by the nightly grep sweep.

## Purpose

A scheduled nightly grep has found an em-dash (U+2014), a non-ASCII glyph in a `.md` file, or a hedging phrase banned by AGENTS.md Section 1. This skill drives an autonomous coding agent to replace the offending content while preserving meaning.

## Trigger conditions

- Nightly prohibited-content grep finds a match.
- Human review flags a banned pattern.
- FlaggedIssue payload lists files and substring matches.

## Install across agents

Maintainer-scoped; end-users of AIGovClaw do not invoke it.

- **Jules:** `npx skills add google-labs-code/jules-skills --skill prohibited-content-sweep --global`.
- **Claude Code:** copy into `~/.claude/skills/prohibited-content-sweep/` or use `jules/skills/install.sh --target claude-code`.
- **Cursor, Gemini CLI, Antigravity:** copy the directory into the agent's skills directory.

## Test locally

```bash
bash /path/to/jules/skills/prohibited-content-sweep/scripts/post-check.sh README.md
```

## Resources

- `resources/prohibited-content.md` - self-contained list of banned glyphs and hedging phrases. Mirrors aigovops `tests/audit/consistency_audit.py`.

## Source

Derived from `jules/playbook/prohibited-content-sweep.md`.
