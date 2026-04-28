# CLAUDE.md

Guidance for Claude Code working on this repository.

## Project context

aigovclaw is the runtime that consumes the skill catalogue at `ZOLAtheCodeX/aigovops`. When making changes that affect skill loading or directory structure here, consider whether the catalogue repo needs a corresponding update.

## Git boundary discipline

Canonical location: `~/Documents/CODING/aigovclaw`
Remote: `https://github.com/ZOLAtheCodeX/aigovclaw.git`
Default branch: `main`

Rules for any AI session working on this project:

1. **Verify location first.** Before any git command, run `pwd && git rev-parse --show-toplevel`. The toplevel must equal the path above.
2. **Never `git init` outside this project root.** Do not create new repositories at `~`, `~/Documents`, `~/Documents/CODING`, or any directory upstream of this one.
3. **Never `git add` or commit from outside this project's tree.** All staging happens from within this directory or its subdirectories.
4. **Worktrees go inside this project, not in `Claude/Projects/`.** Use `git worktree add ./worktrees/<name> <branch>`. Never let Claude Code's `EnterWorktree` provision a worktree under `~/Documents/Claude/Projects/<X>/.claude/worktrees/` — that pattern caused a multi-project entanglement on 2026-04-27 (a stray `~/.git` was silently capturing files from every project under `~/`).

Recovery: see `~/Backups/home-git-archive-2026-04-27/all-branches.bundle` if any older history is ever needed.
