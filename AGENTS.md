# AGENTS.md

Instructions for AI agents (Jules, Claude Code, Codex CLI, Cursor, and others) operating on this repository.

## What this repository is

AIGovClaw is the Hermes Agent configuration package for AIGovOps. It is the runtime that consumes the framework-agnostic catalogue at [aigovops/aigovops](https://github.com/ZOLAtheCodeX/aigovops). This repository contains the installer, the agent persona, the workflow definitions, and the security-scoped Hermes configuration.

This is a configuration repository. It is not a library. It does not export importable modules. It is consumed by humans running `./install.sh` and by Hermes Agent reading the files placed in `~/.hermes/` after install.

## Files that must NEVER be modified autonomously

The following files require a human-approved GitHub issue before any change. Do not edit, rename, or delete them on your own initiative even if the change appears beneficial.

- `persona/SOUL.md`: the agent persona is a load-bearing trust artifact. Persona changes affect every output.
- `SECURITY.md`: security policy changes require explicit review.
- `LICENSE`: license changes require explicit review.
- `config/hermes.yaml`, security section only: the `tools` block defines the agent's permission boundary. Loosening permissions autonomously is prohibited. Other sections of `hermes.yaml` (memory backend, model selection scaffolding, cron schedules) may be edited per the rules below.

## What you can do autonomously with an approved issue

With a referenced issue that has been triaged and assigned, you may:

- Add new workflow stubs under `workflows/` following the existing naming and structure.
- Update `skills/` content (this directory is sourced from [aigovops/aigovops](https://github.com/ZOLAtheCodeX/aigovops); the rule here is that you may sync from the upstream catalogue, not invent new skill content).
- Update non-security steps in `install.sh` (for example, adding a new verification step or improving error messages).
- Update workflow documentation files.
- Update `config/hermes.yaml` sections outside the `tools` security block.

## Authoritative quality standard

The canonical quality standard for all AIGovClaw outputs, and for any content you write in this repository, is [aigovops/STYLE.md](https://github.com/ZOLAtheCodeX/aigovops/blob/main/STYLE.md). Read it before writing anything. The same prohibitions apply here:

- No emojis in any output, file, comment, commit message, or PR description.
- No em-dashes (the U+2014 character).
- No hedging language ("may want to consider", "might be helpful to", "could potentially").
- All framework citations use the formats specified in STYLE.md.

The aigovops repository AGENTS.md ([aigovops/AGENTS.md](https://github.com/ZOLAtheCodeX/aigovops/blob/main/AGENTS.md)) is also authoritative for cross-cutting concerns. Read it.

## Cross-repository coordination

When changes here require corresponding changes in [aigovops/aigovops](https://github.com/ZOLAtheCodeX/aigovops) (or vice versa), open a tracking issue in both repositories and link them. Do not merge half a coordinated change.
