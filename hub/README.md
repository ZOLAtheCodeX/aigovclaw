# AIGovClaw Hub v0

A single-file HTML dashboard that reads the local Hermes evidence store and
renders the composite AI Management System (AIMS) state for an organization.

Static. Local-only. Stdlib Python only. No backend. No framework. No CDN. No
network requests at runtime.

## What this is

The hub is the brand surface for AIGovClaw. Governance leads open it daily to
see the composite state of their AIMS: risk register posture, Statement of
Applicability coverage, AISIA status per AI system, open nonconformities, KPI
breaches, framework gap-assessment scores, EU AI Act classification tiers,
recent Jules maintenance activity, and the queue of items tagged for human
review.

Every number in the hub is a link to the JSON artifact that produced it. This
is the audit trail. Click a count, land on the artifact, read the evidence.

## What this is not

1. Not a web application. There is no login, no session, no server-side state.
2. Not a data warehouse. It reads one local directory tree and stops.
3. Not a replacement for the primary evidence store. The store is canonical.
   The hub is a view.
4. Not a substitute for the ISO audit portal, the NIST evaluation harness, or
   the EU AI Act conformity assessment process. It summarizes the evidence
   those processes produce. It does not replace them.

## Why static and single-file

Governance artifacts need to be inspected in air-gapped, audit, and court
settings. A single self-contained HTML file can be emailed, printed to PDF,
copied to a read-only USB, and archived alongside the evidence bundle that
produced it. A React single-page app with backend and build toolchain cannot.

When the richer interactive view is justified, hub v1 will use React, Tailwind,
and shadcn/ui bundled via the `web-artifacts-builder` skill. That is a
deliberate upgrade, not a default.

## Install

No install step beyond the parent repository clone. The hub is pure stdlib.
Python 3.10 or newer is required.

## Generate a dashboard

```
python3 -m aigovclaw.hub.cli generate --output dashboard.html
```

Open `dashboard.html` in any modern browser.

The hub reads from `~/.hermes/memory/aigovclaw/` by default. Override with:

```
AIGOVCLAW_EVIDENCE_PATH=/path/to/evidence python3 -m aigovclaw.hub.cli generate --output dashboard.html
# or
python3 -m aigovclaw.hub.cli generate --output dashboard.html --evidence /path/to/evidence
```

## Serve the dashboard locally

Drill-down links point to JSON artifact files under the evidence store. For
those links to resolve in a browser, serve the generated HTML and the evidence
tree together:

```
python3 -m aigovclaw.hub.cli serve --port 8080 --open
```

The command uses `http.server` from the standard library. No framework. No
auth. Bind host defaults to `127.0.0.1` so the server is not reachable from
the network.

## Recognized artifact directories

The hub walks the following paths under the evidence root:

| Directory | Purpose |
|---|---|
| `risk-register/` | Risk register artifacts emitted by the risk-register plugin. |
| `soa/` | Statement of Applicability artifacts. |
| `aisia/` | AI System Impact Assessment artifacts, one per system. |
| `nonconformity/` | Nonconformity records. |
| `metrics/` | KPI collector output. |
| `gap-assessment/` | Per-framework gap assessment scores. |
| `classification/` | EU AI Act classifier output per system. |
| `jules/flagged/` | Active FlaggedIssue records for Jules. |
| `jules/archive/` | Closed FlaggedIssue records. |
| `action-required/` | Artifacts routed to the human-action queue by the MCP router. |

Each JSON file is loaded once. For "latest per system" panels, the most
recent file per `system_id` wins, fallen back to file mtime. Files that fail
to parse are skipped silently; they do not abort the render.

## Empty state

If the evidence store is missing or empty, the hub renders a help page that
names the missing path and lists the commands that produce first artifacts.
No placeholders, no fake numbers.

## Design

The hub follows the principles in Anthropic's frontend-design skill
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

The hub does not ship TTF files and does not fetch fonts from the network.
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

```
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
hub does not regenerate that block on reload; edits persist until the next
`generate` call overwrites the file.

## Tests

Standalone runnable:

```
python3 hub/tests/test_generator.py
```

The tests seed a temporary evidence store with one artifact of every supported
type, run the generator, and assert:

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

The hub reads the evidence store. It never writes to it. It does not execute
code from any artifact. It does not resolve remote URLs at render time. The
only network request that can originate from a generated hub is a click by the
human on a Jules PR link, which points to `github.com` only.

The `serve` subcommand binds to `127.0.0.1` by default. Use `--host 0.0.0.0`
only on a trusted network and document the decision.

## Integration boundary

The hub is a read-only consumer of the evidence store. It has no dependency on
`tools/`, `mcp_server/`, or `jules/`. Those modules produce artifacts. The hub
reads them. The one-way dependency is the whole point.

## Future: hub v1

When the user is ready to invest in the richer interactive view, v1 will use:

- React with TypeScript.
- Tailwind for utility styling.
- shadcn/ui for interactive components.
- `web-artifacts-builder` for bundling into a single claude.ai artifact.

v1 will keep the static generated build for audit and archival contexts. It
will add a live mode that reads the evidence store via a thin read-only JSON
endpoint served by the same stdlib process as v0's `serve` command.
