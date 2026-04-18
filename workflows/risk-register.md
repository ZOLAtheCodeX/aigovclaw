# Workflow: risk-register

**Status**: stub. Step content is placeholder. Implementation in Phase 3.

**Primary framework**: ISO/IEC 42001:2023, NIST AI RMF 1.0.

**Output artifact**: AI risk register (CSV + Markdown).

## Objective

Produce and maintain a structured AI risk register with framework-mapped controls. Each register entry identifies a risk, its likelihood and impact, the affected AI system, the applicable framework controls, and the assigned owner.

## Required inputs

- AI system inventory (one or more systems).
- Risk identification source (one of: stakeholder consultation notes, prior incident reports, AISIA outputs, or a hybrid).
- Risk scoring rubric (likelihood scale and impact scale).
- Owner registry (mapping of role to person or team).

## Steps

1. Validate inputs and resolve the framework reference set.
2. Load the relevant catalogue skills.
3. For each identified risk:
   1. Classify by category (for example: bias, robustness, privacy, security, accountability, transparency).
   2. Score likelihood and impact using the supplied rubric.
   3. Map to applicable ISO 42001 Annex A controls and NIST AI RMF subcategories.
   4. Identify a current mitigation if one exists.
   5. Identify a residual risk after current mitigation.
   6. Assign an owner from the supplied owner registry.
4. Sort by residual risk score (high to low).
5. Render as CSV (for spreadsheet ingestion) and Markdown (for human review).

## Quality gates

- Every risk has at least one control mapping with a valid framework citation.
- Every risk has an assigned owner.
- Every risk has a current and residual score.
- The output contains no prohibited language.

## Output artifact specification

Phase 3.
