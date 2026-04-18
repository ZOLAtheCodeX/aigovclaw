# workflows/

This directory holds AIGovClaw workflow definitions. A workflow is an ordered sequence of agent actions that produces a specific governance artifact: an audit log entry, a gap assessment, a risk register, an AI System Impact Assessment.

## Workflow index

| Workflow | Output Artifact | Status |
|---|---|---|
| [audit-log](audit-log.md) | ISO 42001-compliant audit log entry | stub |
| [gap-assessment](gap-assessment.md) | Gap assessment report against ISO 42001 Annex A or NIST AI RMF subcategories | stub |
| [risk-register](risk-register.md) | AI risk register with framework-mapped controls | stub |
| [aisia-runner](aisia-runner.md) | AI System Impact Assessment per ISO 42001 Clause 6.1.4 | stub |

## Workflow file format

Each workflow is a Markdown file with:

1. A frontmatter or header block identifying the workflow name, version, and primary framework reference.
2. A description of the workflow objective and output artifact.
3. A numbered step sequence describing what the agent does.
4. Required inputs.
5. Output artifact specification.
6. Quality gates (validation steps the agent must complete before declaring the workflow done).

## Adding a new workflow

Open an issue first. Workflows define agent behavior and have direct downstream effect on output quality, so additions are reviewed before implementation. Once the issue is approved, add the workflow file following the existing format and register it in the index above.
