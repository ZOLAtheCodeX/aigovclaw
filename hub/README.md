# AIGovClaw Command Centre v0

> Product name: AIGovClaw Command Centre. The codebase directory is `hub/` for
> historical reasons; this is not being renamed because module paths are
> backward-compat-sensitive. CLI subcommands (for example `serve`) and Python
> module paths (`hub.cli`, `hub.v2.cli`) likewise retain the `hub` name.

A single-file HTML dashboard that reads the local Hermes evidence store and
renders the composite AI Management System (AIMS) state for an organization.

Static. Local-only. Stdlib Python only. No backend. No framework. No CDN. No
network requests at runtime.

## What this is

The Command Centre is the brand surface for AIGovClaw. Governance leads open it
daily to see the composite state of their AIMS: risk register posture,
Statement of Applicability coverage, AISIA status per AI system, open
nonconformities, KPI breaches, framework gap-assessment scores, EU AI Act
classification tiers, recent Jules maintenance activity, and the queue of items
tagged for human review.

Every number in the Command Centre is a link to the JSON artifact that produced
it. This is the audit trail. Click a count, land on the artifact, read the
evidence.

## What this is not

1. Not a web application. There is no login, no session, no server-side state.
2. Not a data warehouse. It reads one local directory tree and stops.
3. Not a replacement for the primary evidence store. The store is canonical.
   The Command Centre is a view.
4. Not a substitute for the ISO audit portal, the NIST evaluation harness, or
   the EU AI Act conformity assessment process. It summarizes the evidence
   those processes produce. It does not replace them.

## Why static and single-file

Governance artifacts need to be inspected in air-gapped, audit, and court
settings. A single self-contained HTML file can be emailed, printed to PDF,
copied to a read-only USB, and archived alongside the evidence bundle that
produced it. A React single-page app with backend and build toolchain cannot.

When the richer interactive view is justified, Command Centre v1 will use
React, Tailwind, and shadcn/ui bundled via the `web-artifacts-builder` skill.
That is a deliberate upgrade, not a default.

## Versions

| Capability | v0 | v1 | v2 |
|---|---|---|---|
| Single-file HTML artifact | yes | yes | yes |
| Backend / server state | none | none | none |
| Dependencies | stdlib only | vendored React 18 UMD | vendored React 18 UMD |
| Aesthetic | deep slate + burnt orange, Crimson Pro + JetBrains Mono | same | deep slate-blue (AIGovOS) + burnt orange accent, Plus Jakarta Sans + Source Sans 3 + JetBrains Mono |
| Sidebar IA | none | none | CASCADE / DISCOVERY / ASSURANCE / GOVERNANCE (AIGovOS port) |
| Panel count | ~10 | ~10 | 30+ covering every AIGovOps plugin |
| Jurisdiction filter | Global / USA / EU / UK | same | Global / USA / EU / UK / Singapore / Canada |
| Three-tab workspace per panel (Guidance / Artifacts / Validation) | no | no | yes |
| Cascade intake wizard | no | no | yes (writes `aigovclaw.hub.v2.profile` to localStorage) |
| Crosswalk graph visualization | no | no | yes (inline SVG, data parsed from aigovops) |
| Command palette (`/` shortcut) | no | basic | yes |
| Action-required banner at top | panel | panel | sticky banner + panel |
| Best for | archival, air-gapped | interactive composite view | daily practitioner workflow |

All three versions read from the same `~/.hermes/memory/aigovclaw/` evidence
store. v2 additionally reads crosswalk YAML from the adjacent `aigovops` repo
when available.

Commands:

```bash
python3 -m aigovclaw.hub.cli generate    --output dashboard.html       # v0
python3 -m aigovclaw.hub.cli generate-v1 --output hub-v1.html          # v1
python3 -m aigovclaw.hub.cli generate-v2 --output hub-v2.html          # v2
```

v1 and v2 require the React UMD files dropped into the respective
`hub/v1/vendor/` and `hub/v2/vendor/` directories. Without them, the generator
exits with code 2 and a maintainer-action message.

## Install

No install step beyond the parent repository clone. The Command Centre is pure
stdlib. Python 3.10 or newer is required.

## Generate a dashboard

```bash
python3 -m aigovclaw.hub.cli generate --output dashboard.html
```

Open `dashboard.html` in any modern browser.

The Command Centre reads from `~/.hermes/memory/aigovclaw/` by default. Override
with:

```bash
AIGOVCLAW_EVIDENCE_PATH=/path/to/evidence python3 -m aigovclaw.hub.cli generate --output dashboard.html
# or
python3 -m aigovclaw.hub.cli generate --output dashboard.html --evidence /path/to/evidence
```

## Serve the dashboard locally

Drill-down links point to JSON artifact files under the evidence store. For
those links to resolve in a browser, serve the generated HTML and the evidence
tree together:

```bash
python3 -m aigovclaw.hub.cli serve --port 8080 --open
```

The command uses `http.server` from the standard library. No framework. No
auth. Bind host defaults to `127.0.0.1` so the server is not reachable from
the network.

## Recognized artifact directories

The Command Centre walks the following paths under the evidence root:

| Directory | Purpose |
|---|---|
| `risk-register/` | Risk register artifacts emitted by the risk-register plugin. |
| `soa/` | Statement of Applicability artifacts. |
| `aisia/` | AI System Impact Assessment artifacts, one per system. |
| `nonconformity/` | Nonconformity records. |
| `metrics/` | KPI collector output. |
| `gap-assessment/` | Per-framework gap assessment scores. |
| `classification/` | EU AI Act classifier output per system. |
| `uk-atrs/` | UK Algorithmic Transparency Recording Standard records. |
| `colorado-ai-act/` | Colorado SB 205 artifacts. |
| `nyc-ll144/` | NYC Local Law 144 AEDT bias audit artifacts. |
| `california-ai/` | California ADMT, CCPA, SB 942, AB 2013 artifacts. |
| `jules/flagged/` | Active FlaggedIssue records for Jules. |
| `jules/archive/` | Closed FlaggedIssue records. |
| `action-required/` | Artifacts routed to the human-action queue by the MCP router. |

Each JSON file is loaded once. For "latest per system" panels, the most
recent file per `system_id` wins, fallen back to file mtime. Files that fail
to parse are skipped silently; they do not abort the render.

## Jurisdiction filter

The Command Centre renders a sticky tab bar with four views: Global, USA, EU,
UK. Global
is the default and shows every panel. The other three scope the view to the
panels relevant to that jurisdiction.

| View | Shows | Hides |
|---|---|---|
| Global | All panels. | Nothing. |
| USA | Global panels, USA state-level activity panel, and any panel tagged `usa-*`. | EU-only, UK-only. |
| EU | Global panels and the EU AI Act classification panel. | USA state-level, UK-only. |
| UK | Global panels and the UK ATRS records panel. | USA state-level, EU-only. |

Every panel carries a `data-jurisdiction` attribute. Each artifact may also
carry a top-level `jurisdiction` field that overrides the default mapping from
artifact type to jurisdiction.

### USA state-level panel

The USA view includes a state-level activity table with rows for Colorado
(SB 205), New York City (Local Law 144), and California (CPPA ADMT, CCPA,
SB 942, AB 2013). Counts reflect the number of records under the matching
evidence directory. Empty directories produce a zero-count row rather than
hiding the jurisdiction.

### How filtering works

Filtering is CSS-class based. A small script adds `filter-global`,
`filter-usa`, `filter-eu`, or `filter-uk` to `<body>`. Panels are shown and
hidden via attribute selectors on `data-jurisdiction`. If JavaScript is
disabled the page renders the Global view with all panels visible.

### Persistence

The selected tab is stored in `sessionStorage` and restored on reload. No
cookies. No `localStorage`. The preference is scoped to the browser tab.

### Accessibility

The tab bar implements the ARIA authoring-practices `tablist` pattern.
Arrow keys move focus between tabs, Enter and Space activate the focused
tab, and `aria-selected` reflects the active view. The CSS transition on
view changes respects `prefers-reduced-motion`.

## Empty state

If the evidence store is missing or empty, the Command Centre renders a help
page that names the missing path and lists the commands that produce first
artifacts. No placeholders, no fake numbers.

## Design

The Command Centre follows the principles in Anthropic's frontend-design skill
(https://claude.com/blog/improving-frontend-design-through-skills): distinctive
typography rather than generic system stacks, purposeful color with a single
strong accent rather than purple gradients, layered atmospheric backgrounds
rather than flat fills, intentional micro-interactions rather than gratuitous
motion.

### Typography

Two families, both opinionated, neither generic.

- Display and code: JetBrains Mono. Fallback chain: `ui-monospace`,
  `SFMono-Regular`, `Menlo`, `Consolas`, `monospace`.
- Body and tables: Crimson Pro. Fallback chain: `Georgia`,
  `Iowan Old Style`, `serif`.

The Command Centre does not ship TTF files and does not fetch fonts from the
network.
The user can drop `.ttf` files into `hub/assets/fonts/` and add an
`@font-face` block to a local override CSS if they want first-party font
delivery. Until then the stack falls back to the listed system families.

`Inter`, `Roboto`, and `system-ui` are deliberately excluded. Those stacks
produce the generic "AI dashboard" look the frontend-design brief rejects.

### Color

Dark base with one strong accent. The palette is defined as CSS custom
properties on `:root` and can be overridden without touching the generator.

| Token | Value | Purpose |
|---|---|---|
| `--bg` | `#0f1419` | Primary background (deep slate). |
| `--surface` | `#1a1f26` | Panel surface. |
| `--surface-2` | `#222833` | Tile surface. |
| `--accent` | `#d97757` | Burnt orange. Distinctive, not purple. |
| `--text` | `#e5e7eb` | Primary text. |
| `--text-dim` | `#9ca3af` | Secondary text. |
| `--border` | `#2a2f38` | Hairlines. |
| `--ok` / `--warn` / `--danger` | green / amber / red | Semantic state. |

To override, drop a stylesheet before the inline CSS or edit the variables
block at the top of the generated HTML. For example:

```text
:root {
  --accent: #a3b18a;      /* olive */
  --bg: #111315;
}
```

### Motion and accessibility

- Hover transitions are 160 ms ease and confined to border color and opacity.
- `@media (prefers-reduced-motion: reduce)` disables all transitions.
- `@media (prefers-contrast: more)` strengthens border and secondary text
  contrast.
- Skip-to-content link is the first focusable element.
- Color contrast meets WCAG 2.1 AA for body text on the default background.
- `<meta name="viewport">` is set so the layout collapses to one column on
  screens narrower than 900 pixels.

## Customization

The generator is intentionally small. The file to edit is
`hub/templates/layout.py` (CSS) and `hub/generator.py` (panels and rendering).
Neither uses a third-party template engine, so edits are direct.

To change the color palette without editing source: generate the file, open it,
and modify the `:root` block at the top of the inlined `<style>` element. The
Command Centre does not regenerate that block on reload; edits persist until
the next `generate` call overwrites the file.

## Tests

Standalone runnable:

```bash
python3 hub/tests/test_generator.py
```

The tests seed a temporary evidence store with one artifact of every supported
type, run the generator against it, and assert:

1. Every panel is present by heading.
2. The counts match the seed data exactly.
3. The `AGENT_SIGNATURE` strings appear in the provenance footer.
4. The HTML parses cleanly with `html.parser`.
5. The output contains no U+2014 em-dash.
6. `<meta name="viewport">` is present and `prefers-reduced-motion` is honored
   in the CSS.
7. The empty-state page renders when the store is empty or missing.
8. No external URL references for CSS or JS, no CDN font host references, no
   banned fonts (`Inter`, `Roboto`, `system-ui`, `ui-sans-serif`), no default
   purple accent colors.

## Threat model

The Command Centre reads the evidence store. It never writes to it. It does not
execute code from any artifact. It does not resolve remote URLs at render time.
The only network request that can originate from a generated Command Centre is
a click by the human on a Jules PR link, which points to `github.com` only.

The `serve` subcommand binds to `127.0.0.1` by default. Use `--host 0.0.0.0`
only on a trusted network and document the decision.

## Integration boundary

The Command Centre is a read-only consumer of the evidence store. It has no
dependency on `tools/`, `mcp_server/`, or `jules/`. Those modules produce
artifacts. The Command Centre reads them. The one-way dependency is the whole
point.

## v1: React artifact variant

Command Centre v1 is an optional richer interactive view that coexists with v0.
v0 remains the default portable single-file output and does not change.

| Variant | Default | JavaScript | Use when |
|---|---|---|---|
| v0 | Yes. | Tiny jurisdiction switcher only. | Audit, archive, email, PDF, USB, court. |
| v1 | No. Opt-in. | React 18 + inline app code. | Day-to-day review with sort, filter, collapse, charts. |

v1 matches the v0 aesthetic bar exactly: JetBrains Mono display, Crimson Pro
body, burnt-orange `#d97757` accent on `#0f1419` deep slate. No Inter, no
Roboto, no purple gradients. Same four-jurisdiction tab bar, same read-only
threat model, same single-file output.

### Shape

- React 18 UMD bundles inlined from `hub/v1/vendor/` (maintainer must drop
  the files; see v1/README for sources).
- Hand-curated Tailwind-like CSS subset (~300 rules) embedded inline. No
  Tailwind build step, no npm.
- shadcn-shaped components (`Card`, `Table`, `Tabs`, `Badge`, `Button`,
  `Alert`) re-implemented inline as plain functional React components.
- Inlined JSON data payload, parsed at boot, read-only.

### Generate v1

```bash
python3 -m aigovclaw.hub.cli generate-v1 --output hub-v1.html
# or directly:
python3 -m aigovclaw.hub.v1.cli generate --output hub-v1.html
```

If the vendored React files are missing, the generator exits with a clear
error naming the files and their sources. The generator never fetches over
the network.

### Serve v1

```bash
python3 -m aigovclaw.hub.v1.cli serve --port 8080 --open
```

See `hub/v1/README.md` for full v1 documentation and the maintainer vendor
drop procedure.
