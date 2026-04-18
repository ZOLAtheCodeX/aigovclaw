"""HTML and CSS fragments for the AIGovClaw hub.

All rendering uses stdlib string formatting. No third-party template engine.
No external network resources. All assets inline.

Font stack notes:
  - Heading/display: JetBrains Mono if user drops the TTF into assets/fonts.
    Fallback: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace.
  - Body: Crimson Pro if user drops the TTF into assets/fonts.
    Fallback: Georgia, 'Iowan Old Style', serif.
  - Generic system-ui, Inter, Roboto are deliberately excluded. They produce
    the generic AI dashboard look that the frontend-design brief prohibits.
"""

CSS = """
:root {
  --bg: #0f1419;
  --surface: #1a1f26;
  --surface-2: #222833;
  --accent: #d97757;
  --accent-dim: #8a4a37;
  --text: #e5e7eb;
  --text-dim: #9ca3af;
  --text-faint: #6b7280;
  --border: #2a2f38;
  --ok: #4ade80;
  --warn: #f59e0b;
  --danger: #ef4444;
  --radius: 4px;
  --shadow-1: 0 1px 0 rgba(255,255,255,0.02) inset, 0 1px 2px rgba(0,0,0,0.4);
  --font-display: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --font-body: 'Crimson Pro', Georgia, 'Iowan Old Style', serif;
}

* { box-sizing: border-box; }

html, body {
  margin: 0;
  padding: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
  font-size: 17px;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 15% 10%, rgba(217,119,87,0.06), transparent 40%),
    radial-gradient(circle at 85% 85%, rgba(217,119,87,0.04), transparent 45%),
    linear-gradient(180deg, rgba(255,255,255,0.01), transparent 30%);
  z-index: 0;
}

.wrap {
  position: relative;
  z-index: 1;
  max-width: 1280px;
  margin: 0 auto;
  padding: 48px 32px 96px;
}

header.masthead {
  border-bottom: 1px solid var(--border);
  padding-bottom: 28px;
  margin-bottom: 40px;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 16px;
}

.brand {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.brand .eyebrow {
  font-family: var(--font-display);
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 11px;
  color: var(--accent);
}

h1 {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: 42px;
  line-height: 1.05;
  margin: 0;
  letter-spacing: -0.01em;
}

h1 .pipe {
  color: var(--accent);
  font-weight: 400;
}

.meta {
  font-family: var(--font-display);
  font-size: 12px;
  color: var(--text-dim);
  text-align: right;
}

.meta .path {
  color: var(--text-faint);
  word-break: break-all;
}

h2 {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: 18px;
  letter-spacing: 0.02em;
  margin: 0 0 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
  color: var(--text);
  display: flex;
  align-items: baseline;
  gap: 10px;
}

h2 .num {
  color: var(--accent);
  font-size: 12px;
  letter-spacing: 0.1em;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 40px;
}

@media (max-width: 900px) {
  .grid { grid-template-columns: 1fr; }
  .wrap { padding: 28px 18px 72px; }
  h1 { font-size: 32px; }
}

.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 22px 24px 24px;
  box-shadow: var(--shadow-1);
}

.panel.wide { grid-column: 1 / -1; }

.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-top: 8px;
}

.tile {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: border-color 160ms ease, transform 160ms ease;
}

.tile:hover {
  border-color: var(--accent-dim);
}

.tile .count {
  font-family: var(--font-display);
  font-size: 36px;
  font-weight: 500;
  line-height: 1;
  color: var(--text);
  letter-spacing: -0.02em;
}

.tile .count.accent { color: var(--accent); }
.tile .count.warn { color: var(--warn); }
.tile .count.danger { color: var(--danger); }
.tile .count.ok { color: var(--ok); }

.tile .label {
  font-family: var(--font-display);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-dim);
}

.tile a.source {
  font-family: var(--font-display);
  font-size: 10px;
  color: var(--text-faint);
  text-decoration: none;
  margin-top: 2px;
  letter-spacing: 0.06em;
}

.tile a.source:hover { color: var(--accent); }

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 8px;
  font-size: 15px;
}

table th, table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}

table th {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-dim);
  background: var(--surface-2);
}

table td {
  font-family: var(--font-body);
}

table td.mono, table td .mono {
  font-family: var(--font-display);
  font-size: 13px;
}

.badge {
  display: inline-block;
  font-family: var(--font-display);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid var(--border);
  color: var(--text-dim);
}

.badge.ok { border-color: var(--ok); color: var(--ok); }
.badge.warn { border-color: var(--warn); color: var(--warn); }
.badge.danger { border-color: var(--danger); color: var(--danger); }
.badge.accent { border-color: var(--accent); color: var(--accent); }

a {
  color: var(--accent);
  text-decoration: none;
  border-bottom: 1px dotted var(--accent-dim);
  transition: color 160ms ease, border-color 160ms ease;
}

a:hover { color: var(--text); border-bottom-color: var(--text); }

.empty {
  text-align: center;
  padding: 80px 24px;
  max-width: 640px;
  margin: 0 auto;
}

.empty h1 { font-size: 32px; margin-bottom: 20px; }
.empty p { color: var(--text-dim); margin: 12px 0; }
.empty pre {
  text-align: left;
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 16px;
  border-radius: var(--radius);
  font-family: var(--font-display);
  font-size: 13px;
  color: var(--text);
  overflow-x: auto;
}

footer.provenance {
  margin-top: 48px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
  font-family: var(--font-display);
  font-size: 12px;
  color: var(--text-dim);
}

footer.provenance h2 { font-size: 13px; }

footer.provenance .row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 6px 0;
  border-bottom: 1px dashed var(--border);
}

footer.provenance .row:last-child { border-bottom: none; }

footer.provenance .sig { color: var(--text-faint); word-break: break-all; }

.coverage-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
}

.coverage-bar .label {
  font-family: var(--font-display);
  font-size: 12px;
  min-width: 110px;
  color: var(--text-dim);
}

.coverage-bar .track {
  flex: 1;
  height: 6px;
  background: var(--surface-2);
  border-radius: 3px;
  overflow: hidden;
}

.coverage-bar .fill {
  height: 100%;
  background: var(--accent);
}

.coverage-bar .value {
  font-family: var(--font-display);
  font-size: 13px;
  color: var(--text);
  min-width: 48px;
  text-align: right;
}

@media (prefers-reduced-motion: reduce) {
  * {
    transition: none !important;
    animation: none !important;
  }
}

@media (prefers-contrast: more) {
  :root { --border: #4a4f58; --text-dim: #cbd5e1; }
}

.skip-link {
  position: absolute;
  left: -9999px;
  top: 0;
}
.skip-link:focus {
  left: 16px;
  top: 16px;
  background: var(--accent);
  color: var(--bg);
  padding: 8px 12px;
  z-index: 10;
  border-radius: var(--radius);
}

/* Jurisdiction tab bar */
.jurisdiction-bar {
  position: sticky;
  top: 0;
  z-index: 20;
  background: rgba(15, 20, 25, 0.92);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
  margin: -16px -32px 32px;
  padding: 12px 32px;
}

@media (max-width: 900px) {
  .jurisdiction-bar { margin: -8px -18px 24px; padding: 10px 18px; }
}

.jurisdiction-tabs {
  display: flex;
  gap: 4px;
  list-style: none;
  margin: 0;
  padding: 0;
  flex-wrap: wrap;
}

.jurisdiction-tab {
  font-family: var(--font-display);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  padding: 8px 16px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-faint);
  border-radius: var(--radius);
  cursor: pointer;
  transition: color 120ms ease, border-color 120ms ease, background 120ms ease;
}

.jurisdiction-tab:hover {
  color: var(--text-dim);
  border-color: var(--accent-dim);
}

.jurisdiction-tab[aria-selected="true"] {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--surface-2);
}

.jurisdiction-tab:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

/* Jurisdiction filtering: hide panels outside the active view.
   Default (no class on body) shows everything, matching no-JS fallback. */
.panel {
  transition: opacity 120ms ease;
}

body.filter-usa .panel[data-jurisdiction="eu"],
body.filter-usa .panel[data-jurisdiction="uk"] { display: none; }

body.filter-eu .panel[data-jurisdiction^="usa"],
body.filter-eu .panel[data-jurisdiction="uk"],
body.filter-eu .panel[data-jurisdiction="usa-states"] { display: none; }

body.filter-uk .panel[data-jurisdiction^="usa"],
body.filter-uk .panel[data-jurisdiction="eu"],
body.filter-uk .panel[data-jurisdiction="usa-states"] { display: none; }

/* USA state panel is hidden in every view except USA and Global. */
body.filter-eu .panel[data-jurisdiction="usa-states"],
body.filter-uk .panel[data-jurisdiction="usa-states"] { display: none; }

@media (prefers-reduced-motion: reduce) {
  .panel { transition: none; }
  .jurisdiction-tab { transition: none; }
}
"""


JURISDICTION_JS = """
(function() {
  var KEY = 'aigovclaw.hub.jurisdiction';
  var VALID = ['global', 'usa', 'eu', 'uk'];
  var body = document.body;
  var tablist = document.querySelector('[role="tablist"].jurisdiction-tabs');
  if (!tablist) return;
  var tabs = Array.prototype.slice.call(tablist.querySelectorAll('[role="tab"]'));
  if (tabs.length === 0) return;

  function applyFilter(name) {
    VALID.forEach(function(v) { body.classList.remove('filter-' + v); });
    body.classList.add('filter-' + name);
    tabs.forEach(function(tab) {
      var selected = tab.dataset.jurisdiction === name;
      tab.setAttribute('aria-selected', selected ? 'true' : 'false');
      tab.setAttribute('tabindex', selected ? '0' : '-1');
    });
  }

  function persist(name) {
    try { sessionStorage.setItem(KEY, name); } catch (e) { /* ignore */ }
  }

  function restore() {
    try {
      var stored = sessionStorage.getItem(KEY);
      if (stored && VALID.indexOf(stored) !== -1) return stored;
    } catch (e) { /* ignore */ }
    return 'global';
  }

  tabs.forEach(function(tab, idx) {
    tab.addEventListener('click', function() {
      var name = tab.dataset.jurisdiction;
      applyFilter(name);
      persist(name);
    });
    tab.addEventListener('keydown', function(ev) {
      if (ev.key === 'ArrowRight' || ev.key === 'ArrowLeft') {
        ev.preventDefault();
        var dir = ev.key === 'ArrowRight' ? 1 : -1;
        var next = tabs[(idx + dir + tabs.length) % tabs.length];
        next.focus();
      } else if (ev.key === 'Enter' || ev.key === ' ') {
        ev.preventDefault();
        tab.click();
      }
    });
  });

  applyFilter(restore());
})();
"""


def empty_state(evidence_path: str, generated_at: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="aigovclaw-hub/v0">
<title>AIGovClaw Hub. No evidence yet.</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="empty">
    <div class="brand" style="align-items: center;">
      <span class="eyebrow">AIGovClaw Hub v0</span>
    </div>
    <h1>No evidence yet.</h1>
    <p>The evidence store at this path is empty or missing:</p>
    <pre>{evidence_path}</pre>
    <p>Run a plugin to produce your first artifact. For example:</p>
    <pre>hermes run aigovops.risk-register --input <path>
hermes run aigovops.soa-maintenance
hermes run aigovops.eu-ai-act-classifier</pre>
    <p>Then regenerate this hub:</p>
    <pre>python3 -m aigovclaw.hub.cli generate --output hub.html</pre>
    <p class="meta" style="margin-top: 32px;">Generated {generated_at}</p>
  </div>
</div>
</body>
</html>
"""
