# Workflow: aisia-runner

**Status**: stub. Step content is placeholder. Implementation in Phase 3.

**Primary framework**: ISO/IEC 42001:2023, Clause 6.1.4 (AI System Impact Assessment).

**Output artifact**: AI System Impact Assessment (AISIA) document (Markdown + JSON).

## Objective

Execute an AI System Impact Assessment per ISO/IEC 42001:2023, Clause 6.1.4. The output documents the impact of an AI system on individuals, groups, and society, identifies mitigations, and feeds into the broader risk management process.

## Required inputs

- AI system description: purpose, intended use, decision context, deployment environment.
- Affected stakeholders: individuals, groups, communities affected by the system's outputs.
- Data categories processed.
- Decision authority: whether the system supports human decisions, automates decisions, or operates without human review.
- Reversibility: whether the system's outputs can be reversed and at what cost.

## Steps

1. Validate inputs against the schema defined by Clause 6.1.4.
2. Load the `iso42001` skill from the catalogue.
3. For each affected stakeholder group, identify potential impacts across the dimensions specified by Clause 6.1.4 (including but not limited to: individual rights, group fairness, societal impact, environmental impact, economic impact).
4. Classify each impact by severity and likelihood.
5. Identify existing controls that mitigate each impact.
6. Identify residual impact after existing controls.
7. Recommend additional controls where residual impact is unacceptable.
8. Produce a summary statement that an auditor can use to determine whether the impact assessment satisfies Clause 6.1.4.
9. Render in Markdown and JSON.

## Quality gates

- Every stakeholder group identified in the input is addressed in the output.
- Every impact has a severity classification and a likelihood classification.
- Every impact has at least one control reference (existing or recommended).
- The output explicitly references ISO/IEC 42001:2023, Clause 6.1.4 in the document header.

## Output artifact specification

Phase 3.
