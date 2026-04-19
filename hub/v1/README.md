# AIGovClaw Command Centre v1

An optional richer interactive view of the same evidence store that v0 reads.
v1 does not replace v0. v0 remains the portable single-file default.

## Why both variants exist

| Context | Use |
|---|---|
| Email attachment, PDF print, USB archive, court evidence bundle. | v0. |
| Air-gapped or audit environment with no JavaScript engine. | v0. |
| Day-to-day governance review with filtering, sorting, drill-down. | v1. |
| Fast triage of open action-required items. | v1. |
| Any context where the HTML file must render without a build toolchain. | Either. Both are single-file HTML. |

v0 is pure stdlib, zero JavaScript beyond the tiny jurisdiction switcher, and
will render on anything that parses HTML4. v1 is React 18 + a curated
Tailwind subset + shadcn-shaped components, bundled inline, still a single
file, still offline.

## Aesthetic bar

Identical to v0. Enforced by shared CSS tokens.

- Display and code: JetBrains Mono. Fallback `ui-monospace`, `SFMono-Regular`,
  `Menlo`, `Consolas`, `monospace`.
- Body: Crimson Pro. Fallback `Georgia`, `Iowan Old Style`, `serif`.
- Accent: `#d97757` burnt orange. Background: `#0f1419` deep slate.
- No Inter, no Roboto, no system-ui, no purple gradients.

## Shape

- React 18 UMD bundle inlined from `hub/v1/vendor/react.production.min.js` and
  `hub/v1/vendor/react-dom.production.min.js`. No CDN. No `npm install`.
- A hand-written subset of Tailwind-like utility classes (~300 rules, ~16 KB
  of CSS) embedded inline. Covers only the classes v1 components use. No
  Tailwind build step.
- shadcn-shaped primitives re-implemented inline as plain functional React
  components: `Card`, `CardHeader`, `CardTitle`, `CardContent`, `Table`
  (as `DataTable`), `Tabs`, `Badge`, `Button`, `Alert`.
- Application data inlined as JSON in a `<script type="application/json">`
  block. Parsed at boot. Read-only.

## Maintainer onboarding: vendor files

v1 will refuse to generate if the React UMD bundles are missing. The
generator prints a clear maintainer-action message and exits with code 2.

Drop these two files into `hub/v1/vendor/`:

```text
hub/v1/vendor/react.production.min.js
hub/v1/vendor/react-dom.production.min.js
```

Sources (download offline, verify, commit):

- `https://unpkg.com/react@18/umd/react.production.min.js`
- `https://unpkg.com/react-dom@18/umd/react-dom.production.min.js`

The generator never fetches the files over the network. That is a deliberate
threat-model choice.

## Panels

Same 11 panels as v0, reshaped:

1. Risk register. Tile row with tier and treatment counts.
2. Statement of Applicability. Tile row per canonical status.
3. AISIA coverage. Tile row.
4. Nonconformity. Tile row with median age of open items.
5. KPI posture. Tile row.
6. Gap assessment. Hand-rolled SVG coverage bar chart per framework.
7. EU AI Act classification. Hand-rolled SVG donut with legend.
8. USA state-level activity. Sortable, filterable data table.
9. Action required: human. Sortable, filterable data table with copy-URL.
10. UK ATRS records. Sortable, filterable data table with copy-URL.
11. Provenance footer. AGENT_SIGNATURE per artifact type.

## Interactive features

- Sort any column by clicking the header. Toggles ascending / descending.
- Per-column text filter input below each header.
- Each panel collapses and expands.
- Jurisdiction tab bar at top: Global, USA, EU, UK. Arrow keys move focus.
  Selection persisted in `sessionStorage`.
- `/` focuses the global search input.
- Escape clears the focused search input.
- Copy-artifact-URL button on action-required and UK ATRS rows.

## Non-goals

- No login, no multi-user, no server state.
- No build step. No npm. No esbuild. No Vite.
- No writes to the evidence store.
- No telemetry.
- No external URLs in rendered output. The only clickable outbound links are
  the github.com PR links that already appear in supplied artifact data.
- No light mode. Dark only in v1. Light mode is a v1.1 problem.

## Generate

```python
python3 -m aigovclaw.hub.v1.cli generate --output hub-v1.html
```

Override the evidence path with `--evidence /path` or
`AIGOVCLAW_EVIDENCE_PATH=/path`.

## Serve

```python
python3 -m aigovclaw.hub.v1.cli serve --port 8080 --open
```

Same stdlib `http.server` as v0. Binds to `127.0.0.1` by default.

## Tests

```python
python3 hub/v1/tests/test_v1_generator.py
```

The suite asserts:

- The HTML parses cleanly with `html.parser`.
- A `<div id="root">` React mount point is present.
- At least two `<script>` blocks are present (React bundles + app).
- The inlined data payload is valid JSON and round-trips.
- The output contains no U+2014 em-dash.
- The empty-state page renders when the evidence store is empty.

## Style constraints

No em-dashes, no emojis, no hedging. Enforced by test and by grep on the
directory.
