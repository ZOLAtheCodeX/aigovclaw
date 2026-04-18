# Workflow: audit-log

**Status**: stub. Step content is placeholder. Implementation in Phase 3.

**Primary framework**: ISO/IEC 42001:2023

**Output artifact**: ISO 42001-compliant audit log entry (JSON + Markdown).

## Objective

Generate an audit log entry that documents an AI governance event in a form acceptable as audit evidence under ISO/IEC 42001:2023.

## Required inputs

- AI system identifier and description.
- Governance event description (what happened, when, who was involved).
- Decisions made during the event.
- Evidence references (links, document IDs, or attached artifacts).

## Steps

1. Validate that all required inputs are present. Reject the workflow if any are missing.
2. Load the `iso42001` skill from the catalogue.
3. Map the AI system description to applicable Annex A controls.
4. Map the governance event to the relevant ISO 42001 clause (typically Clause 9 or Clause 7.5).
5. Invoke the `audit-log-generator` plugin from the AIGovOps catalogue.
6. Render the plugin output in both JSON and Markdown formats.
7. Run the quality gate: every framework citation in the output must use the format defined in [STYLE.md](https://github.com/ZOLAtheCodeX/aigovops/blob/main/STYLE.md).
8. Present the output to the user with a summary of the clause and control mappings.

## Quality gates

- All framework citations use the canonical format.
- The output contains no prohibited language (em-dashes, emojis, hedging phrases).
- The output identifies every responsible party referenced in the input.
- The output is timestamped in ISO 8601 format.

## Output artifact specification

Phase 3.
