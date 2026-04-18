# Jules Scheduled Tasks Registry

This file is the mirror registry of Jules scheduled tasks as configured in the Jules web UI. Scheduled tasks are web-UI only. The Jules API does not create, edit, or delete them. Editing is not supported at all: delete and recreate is the only option.

This registry is manually maintained. Drift between this file and the Jules UI is a governance finding. Review cadence: monthly.

## Ownership

Owner: Zola Valashiya.
Review cadence: monthly, first Monday.
Change procedure for any scheduled task:

1. Create the replacement task in the Jules web UI with the new config.
2. Verify it runs once against the target repo and produces the expected PR behavior.
3. Delete the old task in the Jules web UI.
4. Update this registry in the same commit that motivates the change.

## Registry

| task_name                                  | cadence          | playbook                   | target_repo               | created_at | notes                                             |
|--------------------------------------------|------------------|----------------------------|---------------------------|------------|---------------------------------------------------|
| framework-drift-weekly-monday              | weekly / Monday  | framework-drift            | ZOLAtheCodeX/aigovops     | 2026-04-18 | Example row. Replace with real Jules UI entry.    |
| prohibited-content-sweep-weekly-sunday     | weekly / Sunday  | prohibited-content-sweep   | ZOLAtheCodeX/aigovops     | 2026-04-18 | Example row. Replace with real Jules UI entry.    |

## Prompt pattern used in the Jules UI for every row

```text
Run playbook `<playbook-name>` against repo `<target-repo>`.
Read `jules/playbook/<playbook-name>.md` at the repo root for full instructions.
Follow every rule in AGENTS.md and STYLE.md.
```

This pattern keeps the scheduled task definition thin. The real prompt lives in the repo and is version-controlled. Editing the playbook file in the repo changes the effective behavior without touching the scheduled task.
