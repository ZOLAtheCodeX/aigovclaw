# framework-drift

Maintainer-scoped Agent Skill for correcting drift between an authoritative framework source (ISO 42001, NIST AI RMF, or EU AI Act) and the text in an AIGovOps plugin `SKILL.md`.

## Purpose

A framework-monitor process or human reviewer has flagged that an AIGovOps plugin `SKILL.md` paragraph no longer matches its authoritative source. This skill drives an autonomous coding agent to correct the paragraph in place, update citations to STYLE.md format, and open a pull request.

## Trigger conditions

- `framework-monitor` job reports a diff between a cached authoritative source snapshot and a SKILL.md paragraph.
- A FlaggedIssue payload is produced with `target_paths`, `authoritative_url`, and paragraph markers.
- A human has filed an issue with the same shape.

## Install across agents

This skill ships in-repo under `jules/skills/framework-drift/`. It is maintainer-scoped; end-users of AIGovClaw do not invoke it.

- **Jules:** `npx skills add google-labs-code/jules-skills --skill framework-drift --global` (after the directory is mirrored to the Jules-skills registry).
- **Claude Code:** copy `jules/skills/framework-drift/` into `~/.claude/skills/framework-drift/` or link it with `jules/skills/install.sh --target claude-code`.
- **Cursor, Gemini CLI, Antigravity:** copy the directory into the agent's skills directory per its documented convention.

## Test locally

```bash
cd /tmp && mkdir -p skill-test && cd skill-test
echo "paragraph-marker-for-test" > target.md
bash /path/to/jules/skills/framework-drift/scripts/stale-check.sh "test-issue" target.md "paragraph-marker-for-test"
```

Expected: exit 0 with the matching line printed. Change the marker to something absent and re-run to verify exit 1.

## Source

Derived from `jules/playbook/framework-drift.md`. The flat playbook file remains as the input format for the Python dispatcher (`jules/dispatcher.py`). This skill directory is the cross-agent distribution form.
