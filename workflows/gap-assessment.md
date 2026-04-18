# Workflow: gap-assessment

**Status**: stub. Step content is placeholder. Implementation in Phase 3.

**Primary framework**: ISO/IEC 42001:2023 (default), NIST AI RMF 1.0 (configurable).

**Output artifact**: Gap assessment report (Markdown + JSON).

## Objective

Assess an organization's current AI governance state against a target framework and produce a structured gap assessment identifying missing controls, partial coverage, and recommended next steps.

## Required inputs

- Target framework (`iso42001` or `nist-ai-rmf`).
- Current state description: existing policies, processes, AI system inventory, governance roles.
- Scope boundary: which AI systems, business units, or jurisdictions are in scope.

## Steps

1. Validate inputs and resolve the target framework to its canonical skill in the catalogue.
2. Load the target framework skill (for example `iso42001` or `nist-ai-rmf`).
3. Enumerate the framework's controls or subcategories within the scope boundary.
4. For each control or subcategory, classify the current state as one of: covered, partially covered, not covered, not applicable. Each classification must be supported by a citation from the input.
5. For partially-covered and not-covered items, generate a recommended next step.
6. Produce a summary count by classification.
7. Render the assessment in Markdown for human review and JSON for programmatic consumption.

## Quality gates

- Every control or subcategory in the framework is classified.
- Every classification has a supporting citation from the input.
- Framework citations use the format defined in [STYLE.md](https://github.com/ZOLAtheCodeX/aigovops/blob/main/STYLE.md).
- Recommended next steps contain no hedging language.

## Output artifact specification

Phase 3.
