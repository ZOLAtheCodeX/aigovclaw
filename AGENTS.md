# AGENTS.md

Instructions for AI agents (Jules, Claude Code, Codex CLI, Cursor, and others) operating on this repository. Read top to bottom before any action. The authoritative cross-repository quality rules live in [aigovops/AGENTS.md](https://github.com/ZOLAtheCodeX/aigovops/blob/main/AGENTS.md). That file takes precedence where any rule in this file is ambiguous or silent.

## 1. Prohibited content (applies everywhere, no exceptions)

The following are not acceptable in any file, commit message, PR title, PR body, issue title, issue body, code comment, docstring, YAML value, or agent-generated output in this repository.

- **No emojis.** Not in PR titles, not in PR bodies, not in commit messages, not in issue templates, not in file names, not in markdown headings, not in code comments. Plain text only.
- **No em-dashes (the U+2014 character).** Use a colon, a comma, parentheses, or restructure.
- **No hedging language.** Specifically prohibited: `may want to consider`, `might be helpful to`, `could potentially`, `it is possible that`, `you might find`, `we suggest you might`.

If you are an automated agent and your default output style violates these rules, override your default.

## 2. Lane boundaries

This repository is a runtime configuration package. Two lanes:

### Tactical-layer lane (Jules, Copilot, any infrastructure agent)

- `install.sh` except the security-sensitive steps (Hermes verification, permission application). Changes to non-security steps are acceptable with an approved issue.
- `skills/` directory sync scripts and documentation. Skill content itself is sourced from [aigovops](https://github.com/ZOLAtheCodeX/aigovops); this directory is populated at install time.
- `config/hermes.yaml` outside the `tools:` security block. The `tools:` block (filesystem, shell, web, email, calendar permissions) is NOT autonomously editable.
- Workflow documentation improvements in `workflows/*.md` that clarify existing steps without changing their meaning.

### Reasoning-layer lane (Claude Code or a designated reasoning agent; no tactical-agent edits)

- `persona/SOUL.md` (the agent persona is a load-bearing trust artifact).
- `workflows/*.md` step sequences, quality gates, and output artifact specifications. Editorial clarifications to existing steps are dual-lane.
- This file (`AGENTS.md`).

## 3. Files that must NEVER be modified autonomously

These require a human-approved GitHub issue before any change, from any lane.

- `SECURITY.md`
- `LICENSE`
- `persona/SOUL.md`
- `config/hermes.yaml` `tools:` security block (the permission defaults for filesystem, shell, web, email, calendar).

## 4. Quality gates

Every PR must satisfy, regardless of lane or author:

1. No prohibited content (emojis, em-dashes, hedging) in title, body, commit messages, or changed files.
2. PR title follows `<type>: <imperative summary>` with `<type>` from `feat`, `fix`, `chore`, `docs`, `ci`, `test`, `refactor`, `security`. No emoji prefix.
3. Commits are signed off by the author or by the agent's configured author identity.
4. If touching `install.sh`, include a plain-language test note stating how the change was validated (local test, clean-machine test, or deferred to Phase 3).

## 5. What this repository is

AIGovClaw is the Hermes Agent configuration package for AIGovOps. It consumes the framework-agnostic catalogue at [aigovops](https://github.com/ZOLAtheCodeX/aigovops). This repository contains the installer, the agent persona, the workflow definitions, and the security-scoped Hermes configuration. It is not a library and does not export importable modules.

## 6. Authoritative quality standard

The canonical quality standard for all AIGovClaw outputs, and for any content written in this repository, is [aigovops/STYLE.md](https://github.com/ZOLAtheCodeX/aigovops/blob/main/STYLE.md). Read it before writing anything.

## 7. Cross-repository coordination

When changes here require corresponding changes in [aigovops](https://github.com/ZOLAtheCodeX/aigovops) (or vice versa), open a tracking issue in both repositories and link them. Do not merge half a coordinated change.
