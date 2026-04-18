# Jules Scheduled Tasks Registry

This file is the mirror registry of Jules scheduled dispatch across both dispatch mechanisms: GitHub Actions workflows (source of truth in the repo) and Jules web UI scheduled tasks (source of truth in the Jules web app, mirrored here).

GitHub Actions dispatch is the preferred mechanism. Jules web UI scheduled tasks are web-UI only: the Jules API does not create, edit, or delete them, and editing is not supported at all (delete and recreate is the only option). Use web UI only for dispatch patterns that GitHub Actions cannot express.

This registry is manually maintained for the web-UI rows. The GitHub Actions rows are authoritative when the workflow file exists in the repo; drift between this file and either source is a governance finding. Review cadence: monthly.

## Ownership

Owner: Zola Valashiya.
Review cadence: monthly, first Monday.

### Change procedure for GitHub Actions dispatch

1. Edit the workflow file under `.github/workflows/jules-<playbook>.yml` in the target repo.
2. Commit and push to main.
3. Update this registry in the same commit.

### Change procedure for Jules web UI scheduled tasks

1. Create the replacement task in the Jules web UI with the new config.
2. Verify it runs once against the target repo and produces the expected PR behavior.
3. Delete the old task in the Jules web UI.
4. Update this registry in the same commit that motivates the change.

## Registry

| task_name                                   | cadence                  | playbook                   | target_repo               | dispatch_mechanism | created_at | notes                                                                 |
|---------------------------------------------|--------------------------|----------------------------|---------------------------|--------------------|------------|-----------------------------------------------------------------------|
| aigovops-framework-drift                    | weekly / Monday 10:00 UTC| framework-drift            | ZOLAtheCodeX/aigovops     | github-actions     | 2026-04-18 | Also fires on `issues` opened/labeled with `framework-update`.        |
| aigovops-markdown-lint                      | on CI failure            | markdown-lint              | ZOLAtheCodeX/aigovops     | github-actions     | 2026-04-18 | Triggered by `workflow_run` on `CI` completion with conclusion=failure.|
| aigovops-prohibited-content-sweep           | weekly / Sunday 12:00 UTC| prohibited-content-sweep   | ZOLAtheCodeX/aigovops     | github-actions     | 2026-04-18 | Covers U+2014 em-dashes and the canonical hedging list from STYLE.md.  |
| aigovops-link-toc                           | weekly / Monday 11:00 UTC| link-toc                   | ZOLAtheCodeX/aigovops     | github-actions     | 2026-04-18 | Adds missing TOC entries only; removals flagged in PR body.           |
| aigovops-citation-drift                     | weekly / Wednesday 13:00 UTC | citation-drift         | ZOLAtheCodeX/aigovops     | github-actions     | 2026-04-18 | Normalizes ISO, NIST, EU AI Act citation formats per STYLE.md.         |
| aigovops-dep-bump                           | weekly / Tuesday 14:00 UTC| dep-bump                  | ZOLAtheCodeX/aigovops     | github-actions     | 2026-04-18 | One PR per dependency, patch and minor only.                           |
| aigovclaw-framework-drift                   | weekly / Monday 10:00 UTC| framework-drift            | ZOLAtheCodeX/aigovclaw    | github-actions     | 2026-04-18 | Also fires on `issues` opened/labeled with `framework-update`.        |
| aigovclaw-markdown-lint                     | on CI failure            | markdown-lint              | ZOLAtheCodeX/aigovclaw    | github-actions     | 2026-04-18 | Triggered by `workflow_run` on `CI` completion with conclusion=failure.|
| aigovclaw-prohibited-content-sweep          | weekly / Sunday 12:00 UTC| prohibited-content-sweep   | ZOLAtheCodeX/aigovclaw    | github-actions     | 2026-04-18 | Covers U+2014 em-dashes and the canonical hedging list from STYLE.md.  |
| aigovclaw-link-toc                          | weekly / Monday 11:00 UTC| link-toc                   | ZOLAtheCodeX/aigovclaw    | github-actions     | 2026-04-18 | Adds missing TOC entries only; removals flagged in PR body.           |
| aigovclaw-citation-drift                    | weekly / Wednesday 13:00 UTC | citation-drift         | ZOLAtheCodeX/aigovclaw    | github-actions     | 2026-04-18 | Normalizes ISO, NIST, EU AI Act citation formats per STYLE.md.         |
| aigovclaw-dep-bump                          | weekly / Tuesday 14:00 UTC| dep-bump                  | ZOLAtheCodeX/aigovclaw    | github-actions     | 2026-04-18 | One PR per dependency, patch and minor only.                           |

## Dispatch mechanism selection

Use `github-actions` for any dispatch that is:

- Schedule-driven on a cron expression.
- Triggered by a GitHub event (issue opened, label applied, workflow_run completed, PR opened, push).
- Needs version-controlled prompt text that evolves with the repo.
- Requires a preflight secret check or gating logic before invoking Jules.

Use `python-dispatcher` (the local `jules/dispatcher.py`) for any dispatch that must run from Zola's local machine or from a non-GitHub runner, typically for one-off or interactive dispatches that should not be visible in GitHub Actions run history.

Use the Jules web UI only when neither of the above can express the trigger pattern.

## Prompt pattern for Jules web UI rows (if any)

```text
Run playbook `<playbook-name>` against repo `<target-repo>`.
Read `jules/playbook/<playbook-name>.md` at the repo root for full instructions.
Follow every rule in AGENTS.md and STYLE.md.
```

This pattern keeps the scheduled task definition thin. The real prompt lives in the repo and is version-controlled. Editing the playbook file in the repo changes the effective behavior without touching the scheduled task.
