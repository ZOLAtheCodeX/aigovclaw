# AIGovClaw Hub v2

The practitioner-facing dashboard. A single-file HTML artifact that reads the
local Hermes evidence store and renders 30+ panels covering every AIGovOps
plugin, grouped by practitioner verb (CASCADE, DISCOVERY, ASSURANCE,
GOVERNANCE).

## What v2 adds over v0 and v1

| Capability | v0 | v1 | v2 |
|---|---|---|---|
| Single-file HTML | yes | yes | yes |
| Backend | none | none | none |
| React runtime | no | yes | yes |
| shadcn-shaped components | no | yes (8) | yes (15+) |
| Sidebar IA | no | no | yes (CASCADE / DISCOVERY / ASSURANCE / GOVERNANCE) |
| Panel count | 10 | 10 | 30+ |
| Three-tab workspace (Guidance / Artifacts / Validation) | no | no | yes |
| Cascade intake wizard | no | no | yes |
| Crosswalk graph view | no | no | yes (inline SVG) |
| Command palette (/) | no | partial | yes |
| Jurisdiction tab bar | no | yes (4) | yes (6) |
| Action-required banner | panel | panel | top banner + panel |
| Evidence bundle quick action | no | no | yes (every panel) |
| Dark mode | yes | yes | yes |
| Light mode | planned | planned | planned for v2.1 |

## Information architecture

The sidebar groups are adopted verbatim from the archived AIGovOS repo
(see `aigovops/docs/aigovos-import-analysis.md`):

- **CASCADE** regulatory-to-action flow. Regulatory feed, applicability
  assessment, cascade intake wizard.
- **DISCOVERY** knowledge and cross-framework analysis. Crosswalk browser
  with graph view, gap explorer, citation search.
- **ASSURANCE** evidence and validation. AI systems registry, risk register,
  Statement of Applicability, AISIA viewer, audit log, metrics dashboard,
  post-market monitoring, robustness evaluation, bias evaluation, evidence
  bundle inspector, certification readiness, gap assessment.
- **GOVERNANCE** decision-making and attestation. Management review,
  internal audit, role matrix, nonconformity register, incident reporting,
  EU conformity assessment, GPAI obligations, human oversight design,
  supplier and vendor, action-required queue, UK ATRS, Colorado SB 205,
  NYC LL 144, Singapore MAGF, explainability docs, system event log, GenAI
  risk register, EU AI Act classifier, data register.

Plus ungrouped top-of-nav: Dashboard, Certification, Tasks.

## Three-tab workspace pattern

Every panel exposes the same three tabs:

1. **Guidance** the plugin SKILL / regulatory obligations this panel addresses.
2. **Artifacts** the rendered output of the corresponding plugin (tiles,
   tables, coverage bars, graph).
3. **Validation** warnings and gaps surfaced by the plugin or derived here.

This is the AIGovOS Certification clause workflow, generalized to every
panel. It keeps the practitioner motion consistent as they move from
CASCADE panels into ASSURANCE panels.

## Cascade intake wizard

The first thing a new user does. Capture organization name, industry,
jurisdictions, systems, and risk appetite. Persists to browser
`localStorage` under `aigovclaw.hub.v2.profile` so downstream panels can
filter. v2 is otherwise read-only; the wizard is the single write.

Persist to disk later by copying `localStorage` into
`~/.hermes/memory/aigovclaw/hub-v2-profile.json` if you want the profile
to survive browser clears.

## Crosswalk graph

An inline SVG graph of frameworks (nodes) connected by mappings (edges).
Click a node to filter the mappings table below. No external libraries.
Mapping data is parsed from `aigovops/plugins/crosswalk-matrix-builder/data/`
at generate time and inlined into the HTML artifact.

## Generate

```bash
python3 -m aigovclaw.hub.v2.cli generate --output hub-v2.html
```

Without the maintainer-dropped React UMD files in `hub/v2/vendor/`, this
exits with code 2 and prints actionable instructions. See
`hub/v2/vendor/README.md`.

## Serve

```bash
python3 -m aigovclaw.hub.v2.cli serve --port 8080 --open
```

Binds `127.0.0.1` by default; not reachable from the network.

## Non-goals

- No FastAPI or any backend.
- No database. The evidence store at `~/.hermes/memory/aigovclaw/` and the
  crosswalk data under `aigovops/plugins/crosswalk-matrix-builder/data/`
  are the only data sources.
- No auth. No multi-user. No session management.
- No telemetry. No external URLs in rendered HTML.
- No writing artifacts. The cascade intake wizard writes only
  `aigovclaw.hub.v2.profile` in `localStorage`.

## Keyboard shortcuts

- `/` open command palette.
- `Esc` close command palette.
- `Enter` inside the palette opens the top result.
