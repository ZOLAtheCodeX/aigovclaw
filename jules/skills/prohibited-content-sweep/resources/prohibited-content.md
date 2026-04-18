# Prohibited Content (canonical list)

Extracted from aigovops `tests/audit/consistency_audit.py` so this skill is self-contained and does not require reading the audit script from a sibling repo. Source of truth: `https://github.com/ZOLAtheCodeX/aigovops/blob/main/tests/audit/consistency_audit.py`.

## Banned characters

| Codepoint | Character | Rule |
|---|---|---|
| U+2014 | em-dash | Replace with hyphen, colon, comma, parentheses, or sentence split per STYLE.md. |
| Any non-ASCII in `.md` | any emoji or non-ASCII glyph | Delete. Restructure minimally to restore grammar. |

Detection regex (em-dash): `\x{2014}`
Detection regex (non-ASCII in .md): `[^\x00-\x7F]`

## Banned hedging phrases

The following phrases are prohibited in any committed file. Detection is case-insensitive substring match.

- `may want to consider`
- `might be helpful to`
- `could potentially`
- `it is possible that`
- `you might find`
- `we suggest you might`

Repair rule: rewrite the sentence to a direct assertion. If the original claim was genuinely uncertain, replace the hedge with a confidence marker such as `confidence: low` or `confidence: medium` rather than deleting the hedge. Do not change the technical meaning of the sentence.

## Exempt files

The following files reference the banned phrases and characters as data (definitions, audit rules, test fixtures). The sweep skips them:

- `AGENTS.md`
- `STYLE.md`
- `tests/audit/consistency_audit.py`
- This file (`prohibited-content.md`) and sibling skill resource files in `jules/skills/**`.

## Why these rules

Governance outputs are read in audit contexts. Hedging undermines determinations. Em-dashes and emojis are not portable across audit-grade rendering systems. Definite language is part of the certification-grade quality bar.
