# Jules Skills (AIGovClaw maintainer tooling)

See `MAINTAINER-TOOLING.md` for the scope notice. These skills are for repository maintenance only. End-users of AIGovClaw do not invoke them.

This directory mirrors the 8 Jules maintenance playbooks (`jules/playbook/*.md`) as Agent Skills in the open standard compatible with Jules Skills, Claude Code Skills, Cursor, Gemini CLI, and Antigravity.

## Catalog

| Skill | Trigger |
|---|---|
| [framework-drift](framework-drift/) | framework-monitor detects drift between an authoritative source (ISO 42001, NIST AI RMF, EU AI Act) and an AIGovOps plugin SKILL.md paragraph. |
| [test-coverage-gap](test-coverage-gap/) | Coverage scan or human review finds a plugin below the minimum assertion-category threshold. |
| [dep-bump](dep-bump/) | Weekly scan or security advisory surfaces a patch or minor dependency bump. |
| [citation-drift](citation-drift/) | Grep or review finds a citation that does not match STYLE.md canonical format. |
| [markdown-lint](markdown-lint/) | CI markdown lint fails or nightly sweep flags whitespace, heading, list, or fence warnings. |
| [new-plugin-scaffold](new-plugin-scaffold/) | A new plugin contract is designed and an empty scaffold directory must be created. |
| [link-toc](link-toc/) | Nightly link checker finds broken internal anchors or a README TOC is missing sub-docs that exist. |
| [prohibited-content-sweep](prohibited-content-sweep/) | Nightly grep finds em-dash, non-ASCII glyph, or hedging phrase banned by AGENTS.md Section 1. |

## Cross-agent compatibility matrix

All 8 skills share the same open-standard layout (`SKILL.md` with YAML frontmatter, `scripts/`, `resources/`, `assets/`, `README.md`).

| Skill | Jules | Claude Code | Cursor | Gemini CLI | Antigravity |
|---|---|---|---|---|---|
| framework-drift | yes | yes | yes | yes | yes |
| test-coverage-gap | yes | yes | yes | yes | yes |
| dep-bump | yes | yes | yes | yes | yes |
| citation-drift | yes | yes | yes | yes | yes |
| markdown-lint | yes | yes | yes | yes | yes |
| new-plugin-scaffold | yes | yes | yes | yes | yes |
| link-toc | yes | yes | yes | yes | yes |
| prohibited-content-sweep | yes | yes | yes | yes | yes |

`yes` means the skill's frontmatter, scripts, and resources require no agent-specific adaptation. Shell scripts assume POSIX bash; resources are plain markdown. Each agent's discovery convention (frontmatter field names) is consumed directly from the `SKILL.md` frontmatter.

## Install

Use `install.sh --target <agent>` to copy or symlink all 8 skills into a target agent's skills directory.

Supported `--target` values:

- `claude-code` - installs to `~/.claude/skills/<name>/`.
- `jules` - runs `npx skills add` for each skill (requires the skills to be published to the Jules registry first).
- `cursor` - installs to `~/.cursor/skills/<name>/`.
- `gemini-cli` - installs to `~/.gemini/skills/<name>/`.
- `antigravity` - installs to `~/.antigravity/skills/<name>/`.

## Relation to the flat playbooks

`jules/playbook/*.md` are the input format for the Python dispatcher (`jules/dispatcher.py`). They are not removed. The flat playbooks and this `skills/` directory are dual forms of the same content: the dispatcher reads the flat files; cross-agent installations read the skill directories.

## Style rules enforced

All files in this directory:

- Contain no em-dash (U+2014). Hyphens only.
- Contain no emojis.
- Use definite language. No hedging.
- Are UTF-8, LF line endings.
- Shell scripts pass shellcheck and begin with `#!/usr/bin/env bash` and `set -euo pipefail`.
