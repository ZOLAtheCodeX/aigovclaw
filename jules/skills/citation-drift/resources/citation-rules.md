# Citation Rules (canonical)

Extracted from aigovops `STYLE.md` so this skill is self-contained and does not require reading STYLE.md from a sibling repo. Source of truth: `https://github.com/ZOLAtheCodeX/aigovops/blob/main/STYLE.md`.

All framework references must use the exact formats below. Citation precision is part of the certification-grade standard. A correctly-numbered but mis-formatted citation will be rejected.

## ISO/IEC 42001:2023

Format: `ISO/IEC 42001:2023, Clause X.X.X`

Examples:

- `ISO/IEC 42001:2023, Clause 6.1.2`
- `ISO/IEC 42001:2023, Annex A, Control A.6.2.4`
- `ISO/IEC 42001:2023, Clause 8.3`

Use the full standard identifier on first reference in any document. Subsequent references in the same document may use `ISO 42001, Clause X.X.X` for brevity.

Anti-pattern: `ISO/IEC 42001, Clause X.X.X` (missing `:2023` year suffix). Detected by the regex `ISO/IEC 42001(?!:2023)\s*,\s*(Clause|Annex A)`.

## NIST AI RMF 1.0

Format: `<FUNCTION> <Subcategory>` where FUNCTION is one of GOVERN, MAP, MEASURE, MANAGE.

Examples:

- `GOVERN 1.1`
- `MAP 3.5`
- `MEASURE 2.7`
- `MANAGE 4.3`

When referencing the framework as a whole on first use, write `NIST AI Risk Management Framework 1.0 (AI RMF 1.0)`.

## EU AI Act (Regulation (EU) 2024/1689)

Format: `EU AI Act, Article XX, Paragraph X` where applicable.

Examples:

- `EU AI Act, Article 9, Paragraph 2`
- `EU AI Act, Article 14`
- `EU AI Act, Annex III, Point 5`

For Recitals: `EU AI Act, Recital XX`. For Annexes: `EU AI Act, Annex X, Point Y`.

## Repair heuristic

When the flagged citation is the ISO anti-pattern, rewrite to insert `:2023` without touching surrounding prose:

- Before: `ISO/IEC 42001, Clause 6.1.2`
- After: `ISO/IEC 42001:2023, Clause 6.1.2`

For NIST and EU AI Act, the dominant drift mode is missing function prefix (NIST) or missing article number format (EU). Repair by matching the canonical examples above exactly.
