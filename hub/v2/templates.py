"""HTML template fragments for AIGovClaw Hub v2.

v2 is the practitioner-facing dashboard. It ports the AIGovOS information
architecture (CASCADE / DISCOVERY / ASSURANCE / GOVERNANCE sidebar groups,
3-step clause workspace, cascade intake wizard, crosswalk graph) onto the
AIGovOps plugin data model. Single-file HTML. Dark mode only. No backend.

Technical stack:
  - React 18 UMD (vendored from hub/v2/vendor/)
  - Curated Tailwind-subset CSS (hand-written, no build)
  - shadcn-shaped components re-implemented as plain React.createElement calls
  - Panel routing via URL hash for shareable deep links
  - Data inlined as JSON; plugin catalogue and plugin SKILL summaries inlined too
  - Crosswalk mappings inlined in condensed form (id, source_fw, target_fw,
    relationship, confidence) so the Discovery group can filter and graph

Design tokens from the AIGovOS import analysis:
  - Primary (Deep Slate Blue): #102a43, #627d98, #d9e2ec
  - Accent (Hub v1 carryover, used sparingly): #d97757
  - Success / Warning / Danger / Info: #27ab83, #f0b429, #ba2525, #0967d2
  - Typography: Plus Jakarta Sans / Source Sans 3 / JetBrains Mono

No em-dashes, no emojis, no hedging anywhere in the rendered output.
"""

from __future__ import annotations


# --------------------------------------------------------------------------
# CSS: curated Tailwind-subset + AIGovOS-derived design tokens
# --------------------------------------------------------------------------

TAILWIND_SUBSET_CSS = r"""
:root {
  /* Primary: Deep Slate Blue (AIGovOS palette). */
  --primary-50:  #f0f4f8;
  --primary-100: #d9e2ec;
  --primary-200: #bcccdc;
  --primary-300: #9fb3c8;
  --primary-400: #829ab1;
  --primary-500: #627d98;
  --primary-600: #486581;
  --primary-700: #334e68;
  --primary-800: #243b53;
  --primary-900: #102a43;
  --primary-950: #0a1929;

  /* Status tokens. */
  --success: #27ab83;
  --success-dim: #199473;
  --warning: #f0b429;
  --warning-dim: #b48012;
  --danger: #ba2525;
  --danger-dim: #8a1717;
  --info: #0967d2;
  --info-dim: #074ea1;

  /* Single accent carryover from Hub v1 (used sparingly). */
  --accent: #d97757;
  --accent-dim: #8a4a37;

  /* Neutral warm-gray scale. */
  --neutral-50:  #f7f7f8;
  --neutral-100: #e9ecef;
  --neutral-200: #ced4da;
  --neutral-300: #adb5bd;
  --neutral-400: #868e96;
  --neutral-500: #495057;
  --neutral-600: #343a40;
  --neutral-700: #212529;
  --neutral-800: #16181b;
  --neutral-900: #0d0f12;

  /* Semantic surfaces (dark mode is the only mode for v2). */
  --bg:         #0a1929;
  --surface-1:  #102a43;
  --surface-2:  #1a3558;
  --surface-3:  #22406a;
  --border:     #243b53;
  --border-2:   #334e68;
  --text:       #f0f4f8;
  --text-dim:   #bcccdc;
  --text-faint: #829ab1;

  /* Typography. */
  --font-display: 'Plus Jakarta Sans', -apple-system, SF Pro Display, system-ui, sans-serif;
  --font-body:    'Source Sans 3', -apple-system, SF Pro Text, system-ui, sans-serif;
  --font-mono:    'JetBrains Mono', SF Mono, Consolas, monospace;

  /* Spacing and radius. */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --radius: 0.5rem;
  --radius-sm: 0.25rem;
  --radius-lg: 0.75rem;
  --radius-full: 9999px;

  /* Layered shadows. */
  --shadow-xs: 0 1px 2px rgba(0,0,0,0.25);
  --shadow-sm: 0 2px 6px rgba(0,0,0,0.30);
  --shadow-md: 0 6px 16px rgba(0,0,0,0.35);
  --shadow-lg: 0 12px 28px rgba(0,0,0,0.40);
  --shadow-focus: 0 0 0 3px rgba(217,119,87,0.40);
}

* { box-sizing: border-box; }

html, body {
  margin: 0; padding: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
  font-size: 15px;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}

h1,h2,h3,h4,h5 { margin: 0; font-family: var(--font-display); font-weight: 600; letter-spacing: -0.01em; }
p, ul, ol { margin: 0; }
button { font: inherit; cursor: pointer; background: transparent; border: none; color: inherit; }
input, select, textarea { font: inherit; color: inherit; }
a { color: var(--info); text-decoration: none; }
a:hover { color: var(--accent); }
code, pre { font-family: var(--font-mono); font-size: 13px; }

/* Layout primitives. */
.flex { display: flex; }
.inline-flex { display: inline-flex; }
.grid { display: grid; }
.block { display: block; }
.inline-block { display: inline-block; }
.hidden { display: none; }

.flex-row { flex-direction: row; }
.flex-col { flex-direction: column; }
.flex-wrap { flex-wrap: wrap; }
.flex-1 { flex: 1 1 0%; }
.flex-none { flex: none; }
.flex-shrink-0 { flex-shrink: 0; }

.items-start { align-items: flex-start; }
.items-center { align-items: center; }
.items-end { align-items: flex-end; }
.items-baseline { align-items: baseline; }
.items-stretch { align-items: stretch; }
.justify-start { justify-content: flex-start; }
.justify-center { justify-content: center; }
.justify-between { justify-content: space-between; }
.justify-end { justify-content: flex-end; }

.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.gap-4 { gap: 16px; }
.gap-5 { gap: 20px; }
.gap-6 { gap: 24px; }
.gap-8 { gap: 32px; }

.grid-cols-1 { grid-template-columns: 1fr; }
.grid-cols-2 { grid-template-columns: repeat(2, minmax(0,1fr)); }
.grid-cols-3 { grid-template-columns: repeat(3, minmax(0,1fr)); }
.grid-cols-4 { grid-template-columns: repeat(4, minmax(0,1fr)); }
.grid-cols-auto { grid-template-columns: repeat(auto-fit, minmax(200px,1fr)); }

/* Spacing. */
.m-0 { margin: 0; }
.mx-auto { margin-left: auto; margin-right: auto; }
.mt-1 { margin-top: 4px; }
.mt-2 { margin-top: 8px; }
.mt-3 { margin-top: 12px; }
.mt-4 { margin-top: 16px; }
.mt-6 { margin-top: 24px; }
.mt-8 { margin-top: 32px; }
.mb-1 { margin-bottom: 4px; }
.mb-2 { margin-bottom: 8px; }
.mb-3 { margin-bottom: 12px; }
.mb-4 { margin-bottom: 16px; }
.mb-6 { margin-bottom: 24px; }
.mb-8 { margin-bottom: 32px; }
.ml-2 { margin-left: 8px; }
.mr-2 { margin-right: 8px; }

.p-0 { padding: 0; }
.p-1 { padding: 4px; }
.p-2 { padding: 8px; }
.p-3 { padding: 12px; }
.p-4 { padding: 16px; }
.p-5 { padding: 20px; }
.p-6 { padding: 24px; }
.p-8 { padding: 32px; }
.px-2 { padding-left: 8px; padding-right: 8px; }
.px-3 { padding-left: 12px; padding-right: 12px; }
.px-4 { padding-left: 16px; padding-right: 16px; }
.px-6 { padding-left: 24px; padding-right: 24px; }
.py-1 { padding-top: 4px; padding-bottom: 4px; }
.py-2 { padding-top: 8px; padding-bottom: 8px; }
.py-3 { padding-top: 12px; padding-bottom: 12px; }
.py-4 { padding-top: 16px; padding-bottom: 16px; }
.py-6 { padding-top: 24px; padding-bottom: 24px; }

/* Width / height. */
.w-full { width: 100%; }
.w-auto { width: auto; }
.min-w-0 { min-width: 0; }
.max-w-screen { max-width: 1440px; }
.h-full { height: 100%; }
.h-screen { height: 100vh; }
.min-h-screen { min-height: 100vh; }

/* Borders. */
.border { border: 1px solid var(--border); }
.border-2 { border: 2px solid var(--border); }
.border-t { border-top: 1px solid var(--border); }
.border-b { border-bottom: 1px solid var(--border); }
.border-l { border-left: 1px solid var(--border); }
.border-r { border-right: 1px solid var(--border); }
.border-strong { border-color: var(--border-2); }
.border-accent { border-color: var(--accent); }
.border-info { border-color: var(--info); }
.border-success { border-color: var(--success); }
.border-warning { border-color: var(--warning); }
.border-danger { border-color: var(--danger); }
.rounded { border-radius: var(--radius); }
.rounded-sm { border-radius: var(--radius-sm); }
.rounded-lg { border-radius: var(--radius-lg); }
.rounded-full { border-radius: var(--radius-full); }

/* Backgrounds. */
.bg-bg { background: var(--bg); }
.bg-surface-1 { background: var(--surface-1); }
.bg-surface-2 { background: var(--surface-2); }
.bg-surface-3 { background: var(--surface-3); }
.bg-accent { background: var(--accent); }
.bg-info { background: var(--info); }
.bg-transparent { background: transparent; }

/* Text. */
.text-text { color: var(--text); }
.text-dim { color: var(--text-dim); }
.text-faint { color: var(--text-faint); }
.text-accent { color: var(--accent); }
.text-info { color: var(--info); }
.text-success { color: var(--success); }
.text-warning { color: var(--warning); }
.text-danger { color: var(--danger); }

.text-xs { font-size: 11px; }
.text-sm { font-size: 13px; }
.text-base { font-size: 15px; }
.text-md { font-size: 17px; }
.text-lg { font-size: 20px; }
.text-xl { font-size: 24px; }
.text-2xl { font-size: 30px; }
.text-3xl { font-size: 38px; }

.font-display { font-family: var(--font-display); }
.font-body { font-family: var(--font-body); }
.font-mono { font-family: var(--font-mono); }
.font-light { font-weight: 300; }
.font-normal { font-weight: 400; }
.font-medium { font-weight: 500; }
.font-semibold { font-weight: 600; }
.font-bold { font-weight: 700; }

.uppercase { text-transform: uppercase; }
.tracking-wide { letter-spacing: 0.12em; }
.tracking-wider { letter-spacing: 0.18em; }
.text-left { text-align: left; }
.text-right { text-align: right; }
.text-center { text-align: center; }
.leading-tight { line-height: 1.15; }
.leading-snug { line-height: 1.35; }
.break-all { word-break: break-all; }
.truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Positioning. */
.relative { position: relative; }
.absolute { position: absolute; }
.fixed { position: fixed; }
.sticky { position: sticky; }
.top-0 { top: 0; }
.left-0 { left: 0; }
.right-0 { right: 0; }
.bottom-0 { bottom: 0; }
.inset-0 { inset: 0; }
.z-10 { z-index: 10; }
.z-20 { z-index: 20; }
.z-30 { z-index: 30; }
.z-40 { z-index: 40; }
.z-50 { z-index: 50; }

/* Overflow. */
.overflow-hidden { overflow: hidden; }
.overflow-x-auto { overflow-x: auto; }
.overflow-y-auto { overflow-y: auto; }
.overflow-auto { overflow: auto; }

/* Cursors. */
.cursor-pointer { cursor: pointer; }
.select-none { user-select: none; }
.outline-none { outline: none; }

/* Shadow. */
.shadow-sm { box-shadow: var(--shadow-sm); }
.shadow-md { box-shadow: var(--shadow-md); }
.shadow-lg { box-shadow: var(--shadow-lg); }

/* Transitions. */
.transition { transition: all 200ms ease; }
.transition-colors { transition: color 200ms ease, background-color 200ms ease, border-color 200ms ease; }

/* Hover states. */
.hover-accent:hover { color: var(--accent); }
.hover-info:hover { color: var(--info); }
.hover-border-accent:hover { border-color: var(--accent); }
.hover-bg-surface-2:hover { background: var(--surface-2); }
.hover-bg-surface-3:hover { background: var(--surface-3); }

/* Focus. */
.focus-ring:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}

/* Animations. */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes scaleIn {
  from { opacity: 0; transform: scale(0.98); }
  to   { opacity: 1; transform: scale(1); }
}
@keyframes slideInRight {
  from { opacity: 0; transform: translateX(8px); }
  to   { opacity: 1; transform: translateX(0); }
}
.anim-fade-in-up { animation: fadeInUp 200ms ease both; }
.anim-scale-in { animation: scaleIn 200ms ease both; }
.anim-slide-in-right { animation: slideInRight 200ms ease both; }

/* App shell layout. */
.app-shell {
  display: grid;
  grid-template-columns: 260px 1fr;
  min-height: 100vh;
}
.sidebar {
  background: var(--surface-1);
  border-right: 1px solid var(--border);
  padding: 16px 12px;
  overflow-y: auto;
  position: sticky; top: 0; height: 100vh;
}
.sidebar h3 {
  font-size: 10px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--text-faint);
  padding: 12px 8px 6px;
  margin: 0;
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sidebar h3 .chev { font-family: var(--font-mono); font-size: 10px; }
.sidebar .nav-item {
  display: block;
  padding: 6px 10px;
  font-size: 13px;
  color: var(--text-dim);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background-color 150ms ease, color 150ms ease;
  border: 1px solid transparent;
  font-family: var(--font-body);
}
.sidebar .nav-item:hover {
  background: var(--surface-2);
  color: var(--text);
}
.sidebar .nav-item.active {
  background: var(--surface-2);
  color: var(--accent);
  border-color: var(--border-2);
}

.main-col {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.topbar {
  background: var(--surface-1);
  border-bottom: 1px solid var(--border);
  padding: 12px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  position: sticky; top: 0; z-index: 40;
}

.jurisdiction-bar {
  display: flex; gap: 8px; align-items: center;
}
.jurisdiction-bar button {
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-faint);
  border: 1px solid transparent;
}
.jurisdiction-bar button:hover { color: var(--text); }
.jurisdiction-bar button[aria-pressed="true"] {
  color: var(--accent);
  border-color: var(--accent);
  background: rgba(217,119,87,0.08);
}

.action-banner {
  background: rgba(240,180,41,0.08);
  border-bottom: 1px solid var(--warning);
  color: var(--warning);
  padding: 8px 24px;
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 500;
  display: flex; align-items: center; gap: 12px;
}

.content {
  padding: 24px;
  min-width: 0;
  flex: 1;
}

/* shadcn-shaped card. */
.card {
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}
.card h2 {
  font-size: 18px;
  margin-bottom: 4px;
}
.card .desc {
  color: var(--text-dim);
  font-size: 13px;
  margin-bottom: 16px;
}

/* Tabs. */
.tabs {
  display: flex;
  gap: 2px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 16px;
}
.tabs button {
  padding: 8px 16px;
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-faint);
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: color 150ms ease, border-color 150ms ease;
}
.tabs button:hover { color: var(--text); }
.tabs button[aria-selected="true"] {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

/* Badges. */
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-family: var(--font-display);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  border: 1px solid var(--border-2);
  color: var(--text-dim);
}
.badge.ok { color: var(--success); border-color: var(--success); }
.badge.warn { color: var(--warning); border-color: var(--warning); }
.badge.danger { color: var(--danger); border-color: var(--danger); }
.badge.info { color: var(--info); border-color: var(--info); }
.badge.accent { color: var(--accent); border-color: var(--accent); }

/* Buttons. */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.04em;
  border: 1px solid var(--border-2);
  color: var(--text-dim);
  transition: all 150ms ease;
}
.btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}
.btn.primary {
  background: var(--accent);
  color: var(--bg);
  border-color: var(--accent);
}
.btn.primary:hover { background: var(--accent-dim); color: var(--text); border-color: var(--accent-dim); }

/* Input. */
.input {
  width: 100%;
  padding: 6px 10px;
  background: var(--bg);
  border: 1px solid var(--border-2);
  border-radius: var(--radius-sm);
  color: var(--text);
  font-family: var(--font-body);
  font-size: 13px;
}
.input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--shadow-focus);
}

/* Table. */
table { width: 100%; border-collapse: collapse; }
th, td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}
th {
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-faint);
  background: var(--surface-2);
}
td { font-family: var(--font-body); font-size: 14px; }
td.mono, .mono { font-family: var(--font-mono); font-size: 12px; }

/* Alert. */
.alert {
  padding: 12px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-2);
  background: var(--surface-2);
  margin-bottom: 16px;
  font-size: 13px;
}
.alert.warn { border-color: var(--warning); background: rgba(240,180,41,0.06); }
.alert.danger { border-color: var(--danger); background: rgba(186,37,37,0.06); }
.alert.info { border-color: var(--info); background: rgba(9,103,210,0.06); }
.alert.ok { border-color: var(--success); background: rgba(39,171,131,0.06); }

/* Tile. */
.tile {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 14px;
  display: flex; flex-direction: column; gap: 4px;
}
.tile .count {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 600;
  line-height: 1.1;
  color: var(--text);
}
.tile .count.accent { color: var(--accent); }
.tile .count.ok { color: var(--success); }
.tile .count.warn { color: var(--warning); }
.tile .count.danger { color: var(--danger); }
.tile .count.info { color: var(--info); }
.tile .label {
  font-family: var(--font-display);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-faint);
}

/* Coverage bar. */
.bar-track {
  flex: 1;
  height: 6px;
  background: var(--surface-3);
  border-radius: 3px;
  overflow: hidden;
}
.bar-fill { height: 100%; background: var(--accent); transition: width 200ms ease; }

/* Keyboard kbd. */
kbd {
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 2px 6px;
  border: 1px solid var(--border-2);
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  color: var(--text-dim);
}

/* Dialog overlay. */
.dialog-overlay {
  position: fixed; inset: 0;
  background: rgba(10,25,41,0.75);
  z-index: 100;
  display: flex; align-items: center; justify-content: center;
}
.dialog {
  background: var(--surface-1);
  border: 1px solid var(--border-2);
  border-radius: var(--radius);
  padding: 24px;
  max-width: 720px;
  width: 92%;
  max-height: 86vh;
  overflow-y: auto;
  box-shadow: var(--shadow-lg);
  animation: scaleIn 200ms ease;
}

/* Command palette. */
.cmdk {
  position: fixed;
  top: 18vh;
  left: 50%;
  transform: translateX(-50%);
  width: 92%;
  max-width: 640px;
  background: var(--surface-1);
  border: 1px solid var(--border-2);
  border-radius: var(--radius);
  box-shadow: var(--shadow-lg);
  z-index: 110;
  animation: fadeInUp 200ms ease;
}
.cmdk input {
  width: 100%;
  padding: 14px 16px;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--border);
  color: var(--text);
  font-family: var(--font-body);
  font-size: 15px;
}
.cmdk input:focus { outline: none; }
.cmdk .list {
  max-height: 48vh;
  overflow-y: auto;
  padding: 6px;
}
.cmdk .list-item {
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  color: var(--text-dim);
}
.cmdk .list-item:hover,
.cmdk .list-item.active {
  background: var(--surface-2);
  color: var(--text);
}

/* Breadcrumb. */
.breadcrumb {
  display: flex; gap: 8px; align-items: center;
  color: var(--text-faint);
  font-family: var(--font-display);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.breadcrumb .sep { color: var(--border-2); }

/* Skip link. */
.skip-link {
  position: absolute; left: -9999px; top: 0;
}
.skip-link:focus {
  left: 16px; top: 16px;
  background: var(--accent); color: var(--bg);
  padding: 8px 12px; border-radius: var(--radius-sm); z-index: 200;
}

/* Reduced motion. */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation: none !important;
    transition: none !important;
  }
}

@media (prefers-contrast: more) {
  :root {
    --border: #4a5b70;
    --text-dim: #e0e7ef;
  }
}

/* Responsive. */
@media (max-width: 960px) {
  .app-shell { grid-template-columns: 1fr; }
  .sidebar { position: static; height: auto; }
  .grid-cols-2, .grid-cols-3, .grid-cols-4 { grid-template-columns: 1fr; }
}
"""


# --------------------------------------------------------------------------
# App JS: plain React via createElement. No JSX. No build.
# --------------------------------------------------------------------------

APP_JS = r"""
(function() {
  'use strict';
  var e = React.createElement;
  var useState = React.useState;
  var useEffect = React.useEffect;
  var useMemo = React.useMemo;
  var useRef = React.useRef;

  var DATA = window.__AIGOVCLAW_HUB_V2_DATA__ || {};
  var CATALOG = DATA.catalog || { groups: [], panels: {} };
  var PROFILE_KEY = 'aigovclaw.hub.v2.profile';
  var SIDEBAR_KEY = 'aigovclaw.hub.v2.sidebar';
  var JURIS_KEY   = 'aigovclaw.hub.v2.jurisdiction';

  // ------------------------------------------------------------------
  // Utilities
  // ------------------------------------------------------------------

  function cx() {
    var out = [];
    for (var i = 0; i < arguments.length; i++) {
      var v = arguments[i];
      if (typeof v === 'string' && v) out.push(v);
    }
    return out.join(' ');
  }

  function safeGet(key, fallback) {
    try {
      var raw = sessionStorage.getItem(key);
      if (raw == null) return fallback;
      return JSON.parse(raw);
    } catch (err) { return fallback; }
  }

  function safeSet(key, value) {
    try { sessionStorage.setItem(key, JSON.stringify(value)); }
    catch (err) { /* ignore */ }
  }

  // localStorage used for the cascade intake profile so it persists across sessions.
  function profileGet() {
    try {
      var raw = localStorage.getItem(PROFILE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (err) { return null; }
  }

  function profileSet(profile) {
    try { localStorage.setItem(PROFILE_KEY, JSON.stringify(profile)); }
    catch (err) { /* ignore */ }
  }

  function useHashRoute() {
    function parse() {
      var h = (window.location.hash || '').replace(/^#\/?/, '');
      return h || 'dashboard';
    }
    var _r = useState(parse());
    var route = _r[0]; var setRoute = _r[1];
    useEffect(function() {
      function onHash() { setRoute(parse()); }
      window.addEventListener('hashchange', onHash);
      return function() { window.removeEventListener('hashchange', onHash); };
    }, []);
    function navigate(to) {
      window.location.hash = '#/' + to;
    }
    return [route, navigate];
  }

  // ------------------------------------------------------------------
  // shadcn-shaped primitives
  // ------------------------------------------------------------------

  function Card(props) {
    return e('section', {
      className: cx('card anim-fade-in-up', props.className),
      'data-panel': props.panelId,
    }, props.children);
  }

  function CardHeader(props) {
    return e('header', { className: 'mb-4' }, props.children);
  }

  function CardTitle(props) {
    return e('h2', { className: 'font-display font-semibold text-lg' }, props.children);
  }

  function CardDescription(props) {
    return e('p', { className: 'desc' }, props.children);
  }

  function CardContent(props) {
    return e('div', { className: cx(props.className) }, props.children);
  }

  function Badge(props) {
    var tone = props.tone || '';
    return e('span', { className: cx('badge', tone) }, props.children);
  }

  function Button(props) {
    return e('button', {
      type: 'button',
      onClick: props.onClick,
      className: cx('btn focus-ring', props.variant === 'primary' ? 'primary' : '', props.className),
      title: props.title,
      disabled: props.disabled,
    }, props.children);
  }

  function Alert(props) {
    return e('div', { className: cx('alert', props.tone || ''), role: 'alert' }, props.children);
  }

  function Input(props) {
    return e('input', Object.assign({ className: 'input focus-ring', type: 'text' }, props));
  }

  function Select(props) {
    return e('select', Object.assign({ className: 'input focus-ring' }, props), props.children);
  }

  function Tabs(props) {
    var items = props.items;
    var value = props.value;
    var onChange = props.onChange;
    return e('div', null,
      e('div', { className: 'tabs', role: 'tablist' }, items.map(function(it) {
        var selected = it.value === value;
        return e('button', {
          key: it.value,
          role: 'tab',
          'aria-selected': selected ? 'true' : 'false',
          onClick: function() { onChange(it.value); },
        }, it.label);
      })),
      e('div', { role: 'tabpanel' }, props.children)
    );
  }

  function Dialog(props) {
    if (!props.open) return null;
    return e('div', {
      className: 'dialog-overlay',
      onClick: function(ev) { if (ev.target === ev.currentTarget) props.onClose(); },
      role: 'dialog',
      'aria-modal': 'true',
    },
      e('div', { className: 'dialog' }, props.children)
    );
  }

  function Breadcrumb(props) {
    var items = props.items || [];
    var out = [];
    items.forEach(function(it, i) {
      if (i > 0) out.push(e('span', { key: 's' + i, className: 'sep' }, '>'));
      out.push(e('span', { key: 'i' + i }, it));
    });
    return e('nav', { className: 'breadcrumb', 'aria-label': 'Breadcrumb' }, out);
  }

  // ------------------------------------------------------------------
  // Sidebar
  // ------------------------------------------------------------------

  function Sidebar(props) {
    var collapsed = props.collapsed;
    var setCollapsed = props.setCollapsed;
    var route = props.route;
    var nav = props.navigate;

    function toggle(group) {
      var next = Object.assign({}, collapsed);
      next[group] = !next[group];
      setCollapsed(next);
      safeSet(SIDEBAR_KEY, next);
    }

    var groups = CATALOG.groups || [];
    return e('aside', { className: 'sidebar', 'aria-label': 'Primary navigation' },
      e('div', { className: 'mb-4 px-2' },
        e('div', { className: 'font-display text-xs tracking-wider uppercase text-accent mb-1' }, 'AIGovClaw'),
        e('div', { className: 'font-display font-semibold text-md text-text' }, 'Hub v2')
      ),
      // Ungrouped items.
      e('div', { className: 'mb-2' },
        ['dashboard', 'certification', 'tasks'].map(function(key) {
          var active = route === key;
          var label = key === 'dashboard' ? 'Dashboard'
                   : key === 'certification' ? 'Certification'
                   : 'Tasks';
          return e('a', {
            key: key,
            href: '#/' + key,
            className: cx('nav-item', active ? 'active' : ''),
            onClick: function(ev) { ev.preventDefault(); nav(key); },
          }, label);
        })
      ),
      groups.map(function(grp) {
        var isOpen = !collapsed[grp.id];
        return e('div', { key: grp.id, className: 'mb-2' },
          e('h3', {
            onClick: function() { toggle(grp.id); },
            role: 'button',
            tabIndex: 0,
            onKeyDown: function(ev) {
              if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); toggle(grp.id); }
            },
            'aria-expanded': isOpen ? 'true' : 'false',
          }, grp.label, e('span', { className: 'chev' }, isOpen ? '-' : '+')),
          isOpen ? e('div', null, grp.items.map(function(item) {
            var active = route === item.id;
            return e('a', {
              key: item.id,
              href: '#/' + item.id,
              className: cx('nav-item', active ? 'active' : ''),
              onClick: function(ev) { ev.preventDefault(); nav(item.id); },
            }, item.label);
          })) : null
        );
      })
    );
  }

  // ------------------------------------------------------------------
  // Jurisdiction bar
  // ------------------------------------------------------------------

  function JurisdictionBar(props) {
    var active = props.value;
    var onChange = props.onChange;
    var JURISDICTIONS = [
      { value: 'global',    label: 'Global' },
      { value: 'usa',       label: 'USA' },
      { value: 'eu',        label: 'EU' },
      { value: 'uk',        label: 'UK' },
      { value: 'singapore', label: 'Singapore' },
      { value: 'canada',    label: 'Canada' },
    ];
    return e('div', { className: 'jurisdiction-bar', role: 'group', 'aria-label': 'Filter by jurisdiction' },
      JURISDICTIONS.map(function(j) {
        return e('button', {
          key: j.value,
          'aria-pressed': j.value === active ? 'true' : 'false',
          onClick: function() {
            onChange(j.value);
            try { sessionStorage.setItem(JURIS_KEY, j.value); } catch (err) { /* ignore */ }
          },
        }, j.label);
      })
    );
  }

  // ------------------------------------------------------------------
  // Action-required banner
  // ------------------------------------------------------------------

  function ActionBanner(props) {
    var rows = (props.data && props.data.rows) || [];
    if (rows.length === 0) return null;
    return e('div', { className: 'action-banner', role: 'status' },
      e('span', { className: 'badge warn' }, String(rows.length)),
      e('span', null, 'Items flagged action-required-human. '),
      e('a', {
        href: '#/action-required',
        onClick: function(ev) { ev.preventDefault(); window.location.hash = '#/action-required'; },
      }, 'Review queue')
    );
  }

  // ------------------------------------------------------------------
  // Three-tab workspace
  // ------------------------------------------------------------------

  function ThreeTabWorkspace(props) {
    var _tab = useState('guidance');
    var tab = _tab[0]; var setTab = _tab[1];
    return e('div', { className: 'anim-fade-in-up' },
      e(Tabs, {
        items: [
          { value: 'guidance',   label: 'Guidance' },
          { value: 'artifacts',  label: 'Artifacts' },
          { value: 'validation', label: 'Validation' },
        ],
        value: tab,
        onChange: setTab,
      },
        tab === 'guidance'   ? (props.guidance  || e('p', { className: 'text-dim text-sm' }, 'No guidance loaded.')) :
        tab === 'artifacts'  ? (props.artifacts || e('p', { className: 'text-dim text-sm' }, 'No artifacts yet. Run the plugin to produce one.')) :
                               (props.validation|| e('p', { className: 'text-dim text-sm' }, 'No validation output.'))
      )
    );
  }

  // ------------------------------------------------------------------
  // Tile row
  // ------------------------------------------------------------------

  function TileRow(props) {
    return e('div', { className: 'grid grid-cols-auto gap-3 mb-4' },
      (props.tiles || []).map(function(t, i) {
        return e('div', { key: i, className: 'tile' },
          e('span', { className: cx('count', t.tone || '') }, String(t.count)),
          e('span', { className: 'label' }, t.label)
        );
      })
    );
  }

  function CoverageBar(props) {
    var pct = Math.max(0, Math.min(100, props.pct || 0));
    return e('div', { className: 'flex items-center gap-3 mb-2' },
      e('span', { className: 'font-display text-xs text-dim', style: { minWidth: 140 } }, props.label),
      e('div', { className: 'bar-track' }, e('div', { className: 'bar-fill', style: { width: pct.toFixed(1) + '%' } })),
      e('span', { className: 'font-display text-xs', style: { minWidth: 42, textAlign: 'right' } }, pct.toFixed(0) + '%')
    );
  }

  // ------------------------------------------------------------------
  // Crosswalk graph (inline SVG)
  // ------------------------------------------------------------------

  function CrosswalkGraph(props) {
    var nodes = props.nodes || [];
    var edges = props.edges || [];
    var _sel = useState(null);
    var sel = _sel[0]; var setSel = _sel[1];

    var W = 640; var H = 360;
    var cx0 = W/2; var cy0 = H/2;
    var R = Math.min(W, H) * 0.36;
    var n = nodes.length || 1;
    var layout = nodes.map(function(node, i) {
      var angle = (2 * Math.PI * i) / n - Math.PI/2;
      return {
        id: node.id,
        label: node.label,
        x: cx0 + R * Math.cos(angle),
        y: cy0 + R * Math.sin(angle),
        count: node.count,
      };
    });
    var byId = {};
    layout.forEach(function(p) { byId[p.id] = p; });

    function onSelect(id) { setSel(sel === id ? null : id); }

    return e('div', null,
      e('svg', {
        width: '100%',
        viewBox: '0 0 ' + W + ' ' + H,
        'aria-label': 'Crosswalk graph',
        style: { maxHeight: 420, background: 'var(--surface-2)', borderRadius: 8 },
      },
        edges.map(function(edge, i) {
          var a = byId[edge.a]; var b = byId[edge.b];
          if (!a || !b) return null;
          var active = sel == null || sel === edge.a || sel === edge.b;
          var weight = Math.max(1, Math.min(6, Math.log(1 + edge.count) * 1.4));
          return e('line', {
            key: i,
            x1: a.x, y1: a.y, x2: b.x, y2: b.y,
            stroke: active ? 'var(--accent)' : 'var(--border-2)',
            strokeWidth: weight,
            strokeOpacity: active ? 0.6 : 0.2,
          });
        }),
        layout.map(function(p) {
          var active = sel === p.id;
          return e('g', { key: p.id, style: { cursor: 'pointer' }, onClick: function() { onSelect(p.id); } },
            e('circle', {
              cx: p.x, cy: p.y,
              r: Math.max(14, Math.min(34, 8 + Math.sqrt(p.count) * 1.8)),
              fill: active ? 'var(--accent)' : 'var(--surface-3)',
              stroke: 'var(--border-2)',
              strokeWidth: 2,
            }),
            e('text', {
              x: p.x, y: p.y + 4,
              textAnchor: 'middle',
              fontSize: 10,
              fontFamily: 'var(--font-display)',
              fill: active ? 'var(--bg)' : 'var(--text)',
            }, p.label),
            e('text', {
              x: p.x, y: p.y + 50,
              textAnchor: 'middle',
              fontSize: 10,
              fontFamily: 'var(--font-mono)',
              fill: 'var(--text-faint)',
            }, String(p.count) + ' mappings')
          );
        })
      ),
      e('p', { className: 'text-faint text-xs mt-2 font-mono' },
        sel ? ('Filtered to ' + sel + '. Click again to clear.') : 'Click a node to filter the crosswalk table below.'),
      e(CrosswalkTable, { mappings: props.mappings || [], filter: sel })
    );
  }

  function CrosswalkTable(props) {
    var filter = props.filter;
    var _q = useState('');
    var q = _q[0]; var setQ = _q[1];
    var rows = useMemo(function() {
      var out = (props.mappings || []).slice();
      if (filter) {
        out = out.filter(function(r) { return r.source_fw === filter || r.target_fw === filter; });
      }
      if (q) {
        var ql = q.toLowerCase();
        out = out.filter(function(r) {
          return (r.id || '').toLowerCase().indexOf(ql) !== -1
              || (r.source_ref || '').toLowerCase().indexOf(ql) !== -1
              || (r.target_ref || '').toLowerCase().indexOf(ql) !== -1;
        });
      }
      return out.slice(0, 100);
    }, [props.mappings, filter, q]);
    return e('div', { className: 'mt-4' },
      e(Input, { placeholder: 'Filter mappings by id or reference', value: q, onChange: function(ev) { setQ(ev.target.value); } }),
      e('div', { className: 'overflow-x-auto mt-2' },
        e('table', null,
          e('thead', null, e('tr', null,
            e('th', null, 'Source framework'),
            e('th', null, 'Source ref'),
            e('th', null, 'Target framework'),
            e('th', null, 'Target ref'),
            e('th', null, 'Relationship'),
            e('th', null, 'Confidence')
          )),
          e('tbody', null, rows.map(function(r, i) {
            return e('tr', { key: i },
              e('td', null, e(Badge, { tone: 'info' }, r.source_fw)),
              e('td', { className: 'mono' }, r.source_ref),
              e('td', null, e(Badge, { tone: 'accent' }, r.target_fw)),
              e('td', { className: 'mono' }, r.target_ref),
              e('td', null, r.relationship || '-'),
              e('td', null, e(Badge, { tone: (r.confidence === 'high' ? 'ok' : r.confidence === 'medium' ? 'warn' : '') }, r.confidence || '-'))
            );
          }))
        )
      ),
      e('p', { className: 'text-faint text-xs mt-2 font-mono' },
        'Showing ' + rows.length + ' of ' + (props.mappings || []).length + ' mappings.')
    );
  }

  // ------------------------------------------------------------------
  // Panels: content factory per panel id. Every panel uses ThreeTabWorkspace
  // so the Guidance / Artifacts / Validation pattern is consistent.
  // ------------------------------------------------------------------

  function PanelHeader(props) {
    return e('div', { className: 'mb-4' },
      e(Breadcrumb, { items: props.crumbs || [] }),
      e('h1', { className: 'font-display font-semibold text-2xl mt-2' }, props.title),
      props.desc ? e('p', { className: 'text-dim text-sm mt-1' }, props.desc) : null
    );
  }

  function Guidance(props) {
    var panelMeta = (CATALOG.panels || {})[props.panelId] || {};
    var skill = panelMeta.skill || '';
    var plugin = panelMeta.plugin || '';
    return e('div', null,
      e('p', { className: 'text-dim text-sm mb-3' }, panelMeta.description || 'Plugin guidance.'),
      plugin ? e('div', { className: 'mb-2' },
        e('span', { className: 'text-faint text-xs uppercase tracking-wide font-display' }, 'Plugin'),
        e('div', { className: 'mono text-sm mt-1' }, plugin)
      ) : null,
      skill ? e('div', { className: 'mb-2' },
        e('span', { className: 'text-faint text-xs uppercase tracking-wide font-display' }, 'Skill source'),
        e('div', { className: 'mono text-sm mt-1' }, skill)
      ) : null,
      panelMeta.frameworks && panelMeta.frameworks.length
        ? e('div', { className: 'mt-3 flex flex-wrap gap-2' },
            panelMeta.frameworks.map(function(f, i) {
              return e(Badge, { key: i, tone: 'info' }, f);
            }))
        : null
    );
  }

  function ArtifactsGeneric(props) {
    // Generic placeholder used when the evidence store is empty for this panel.
    return e('div', null,
      e('p', { className: 'text-dim text-sm mb-3' }, 'No artifacts produced for this plugin yet.'),
      e('div', { className: 'bg-surface-2 border rounded p-3 mono text-xs' },
        'aigovops.' + (props.panelId || '') + ' produces JSON under ~/.hermes/memory/aigovclaw/'
      )
    );
  }

  function ValidationGeneric(props) {
    return e('p', { className: 'text-dim text-sm' }, 'No warnings or gaps reported.');
  }

  function EvidenceQuickAction(props) {
    return e('div', { className: 'mt-4' },
      e(Button, {
        title: 'Open evidence bundle inspector with this panel pre-selected',
        onClick: function() { window.location.hash = '#/evidence-bundle-packager'; },
      }, 'Inspect evidence bundle')
    );
  }

  // Panel dispatch. Each returns the full PanelHeader + card + workspace.
  function Panel(props) {
    var id = props.id;
    var meta = (CATALOG.panels || {})[id] || {};
    var title = meta.title || id;
    var desc = meta.description || '';
    var crumbs = meta.group ? ['Home', meta.group, title] : ['Home', title];

    // Specific renderers.
    if (id === 'crosswalk') {
      var crossData = DATA.crosswalk || { nodes: [], edges: [], mappings: [] };
      return e('div', null,
        e(PanelHeader, { crumbs: crumbs, title: title, desc: desc }),
        e(Card, { panelId: id },
          e(ThreeTabWorkspace, {
            guidance:   e(Guidance, { panelId: id }),
            artifacts:  e('div', null,
              e('p', { className: 'text-dim text-sm mb-3' },
                'Framework-to-framework coverage graph. ' + (crossData.mappings || []).length + ' mappings across ' + (crossData.nodes || []).length + ' frameworks.'),
              e(CrosswalkGraph, crossData),
              e(EvidenceQuickAction, null)
            ),
            validation: e('p', { className: 'text-dim text-sm' },
              'Low-confidence mappings: ' + ((crossData.mappings || []).filter(function(m) { return m.confidence === 'low'; }).length)),
          })
        )
      );
    }

    if (id === 'cascade-intake') {
      return e(CascadeIntakePanel, { meta: meta });
    }

    if (id === 'dashboard') {
      return e(Dashboard, { meta: meta });
    }

    if (id === 'risk-register-builder') {
      return e('div', null,
        e(PanelHeader, { crumbs: crumbs, title: title, desc: desc }),
        e(Card, { panelId: id },
          e(ThreeTabWorkspace, {
            guidance:  e(Guidance, { panelId: id }),
            artifacts: e('div', null,
              e(TileRow, { tiles: [
                { count: (DATA.risk && DATA.risk.total) || 0, label: 'Total rows', tone: 'accent' },
                { count: (DATA.risk && DATA.risk.by_tier && DATA.risk.by_tier.high) || 0, label: 'Tier: high', tone: 'danger' },
                { count: (DATA.risk && DATA.risk.by_tier && DATA.risk.by_tier.medium) || 0, label: 'Tier: medium', tone: 'warn' },
                { count: (DATA.risk && DATA.risk.by_tier && DATA.risk.by_tier.low) || 0, label: 'Tier: low' },
              ]}),
              e(EvidenceQuickAction, null)
            ),
            validation: e(ValidationGeneric, null),
          })
        )
      );
    }

    if (id === 'soa-generator') {
      var soa = DATA.soa || { by_status: {} };
      var statuses = ['included-implemented', 'included-planned', 'included-partial', 'excluded-not-applicable', 'excluded-risk-accepted'];
      return e('div', null,
        e(PanelHeader, { crumbs: crumbs, title: title, desc: desc }),
        e(Card, { panelId: id },
          e(ThreeTabWorkspace, {
            guidance:  e(Guidance, { panelId: id }),
            artifacts: e(TileRow, { tiles: statuses.map(function(s) {
              return {
                count: (soa.by_status && soa.by_status[s]) || 0,
                label: s.replace(/-/g, ' '),
                tone: s === 'included-implemented' ? 'ok' : (s.indexOf('included') === 0 ? 'accent' : ''),
              };
            })}),
            validation: e(ValidationGeneric, null),
          })
        )
      );
    }

    if (id === 'gap-assessment') {
      var gap = DATA.gap || { frameworks: [] };
      return e('div', null,
        e(PanelHeader, { crumbs: crumbs, title: title, desc: desc }),
        e(Card, { panelId: id },
          e(ThreeTabWorkspace, {
            guidance:  e(Guidance, { panelId: id }),
            artifacts: e('div', null,
              (gap.frameworks || []).map(function(fw, i) {
                return e(CoverageBar, { key: i, label: fw.label, pct: fw.pct });
              }),
              e(EvidenceQuickAction, null)
            ),
            validation: e(ValidationGeneric, null),
          })
        )
      );
    }

    if (id === 'action-required') {
      var ar = (DATA.action_required && DATA.action_required.rows) || [];
      return e('div', null,
        e(PanelHeader, { crumbs: crumbs, title: title, desc: desc }),
        e(Card, { panelId: id },
          e(ThreeTabWorkspace, {
            guidance:  e(Guidance, { panelId: id }),
            artifacts: ar.length === 0
              ? e('p', { className: 'text-dim text-sm' }, 'Queue is empty.')
              : e('div', { className: 'overflow-x-auto' },
                  e('table', null,
                    e('thead', null, e('tr', null, e('th', null, 'Item'), e('th', null, 'Flag'))),
                    e('tbody', null, ar.map(function(r, i) {
                      return e('tr', { key: i },
                        e('td', null, r.title),
                        e('td', null, e(Badge, { tone: 'warn' }, r.reason))
                      );
                    }))
                  )
                ),
            validation: e('p', { className: 'text-dim text-sm' }, 'Items remain in queue until resolved.'),
          })
        )
      );
    }

    // Generic fallback: all other panels render ThreeTabWorkspace with generic content.
    return e('div', null,
      e(PanelHeader, { crumbs: crumbs, title: title, desc: desc }),
      e(Card, { panelId: id },
        e(ThreeTabWorkspace, {
          guidance:   e(Guidance, { panelId: id }),
          artifacts:  e('div', null, e(ArtifactsGeneric, { panelId: id }), e(EvidenceQuickAction, null)),
          validation: e(ValidationGeneric, null),
        })
      )
    );
  }

  // ------------------------------------------------------------------
  // Cascade intake wizard
  // ------------------------------------------------------------------

  function CascadeIntakePanel(props) {
    var _profile = useState(profileGet() || {
      organization: '',
      industry: '',
      jurisdictions: [],
      systems: [],
      risk_appetite: 'moderate',
    });
    var profile = _profile[0]; var setProfile = _profile[1];
    var _saved = useState(null);
    var saved = _saved[0]; var setSaved = _saved[1];

    function update(field, value) {
      var next = Object.assign({}, profile);
      next[field] = value;
      setProfile(next);
    }

    function save() {
      profileSet(profile);
      setSaved(new Date().toISOString());
    }

    var JURIS_OPTIONS = [
      { value: 'usa', label: 'USA (federal + state)' },
      { value: 'eu', label: 'EU (AI Act)' },
      { value: 'uk', label: 'UK (ATRS)' },
      { value: 'singapore', label: 'Singapore (MAGF)' },
      { value: 'canada', label: 'Canada' },
    ];

    return e('div', null,
      e(PanelHeader, { crumbs: ['Home', 'CASCADE', 'Cascade intake'], title: 'Cascade intake wizard', desc: 'Capture organization posture once. Downstream panels filter accordingly.' }),
      e(Card, { panelId: 'cascade-intake' },
        e('div', { className: 'grid grid-cols-2 gap-4' },
          e('label', { className: 'flex flex-col gap-1' },
            e('span', { className: 'font-display text-xs uppercase tracking-wide text-faint' }, 'Organization name'),
            e(Input, { value: profile.organization, onChange: function(ev) { update('organization', ev.target.value); } })
          ),
          e('label', { className: 'flex flex-col gap-1' },
            e('span', { className: 'font-display text-xs uppercase tracking-wide text-faint' }, 'Industry'),
            e(Input, { value: profile.industry, onChange: function(ev) { update('industry', ev.target.value); }, placeholder: 'healthcare, financial, public sector, ...' })
          ),
          e('label', { className: 'flex flex-col gap-1' },
            e('span', { className: 'font-display text-xs uppercase tracking-wide text-faint' }, 'Risk appetite'),
            e(Select, {
              value: profile.risk_appetite,
              onChange: function(ev) { update('risk_appetite', ev.target.value); },
            },
              e('option', { value: 'low' }, 'Low'),
              e('option', { value: 'moderate' }, 'Moderate'),
              e('option', { value: 'elevated' }, 'Elevated')
            )
          ),
          e('label', { className: 'flex flex-col gap-1' },
            e('span', { className: 'font-display text-xs uppercase tracking-wide text-faint' }, 'Systems (comma separated)'),
            e(Input, {
              value: (profile.systems || []).join(', '),
              onChange: function(ev) {
                update('systems', ev.target.value.split(',').map(function(s) { return s.trim(); }).filter(Boolean));
              },
              placeholder: 'triage-v1, underwriting-gpai-01',
            })
          )
        ),
        e('fieldset', { className: 'border rounded p-3 mt-4' },
          e('legend', { className: 'font-display text-xs uppercase tracking-wide text-faint px-1' }, 'Jurisdictions that apply'),
          e('div', { className: 'flex flex-wrap gap-3 mt-2' },
            JURIS_OPTIONS.map(function(opt) {
              var checked = (profile.jurisdictions || []).indexOf(opt.value) !== -1;
              return e('label', { key: opt.value, className: 'flex items-center gap-2 text-sm' },
                e('input', {
                  type: 'checkbox',
                  checked: checked,
                  onChange: function() {
                    var cur = (profile.jurisdictions || []).slice();
                    var i = cur.indexOf(opt.value);
                    if (i === -1) cur.push(opt.value); else cur.splice(i, 1);
                    update('jurisdictions', cur);
                  },
                }),
                e('span', null, opt.label)
              );
            })
          )
        ),
        e('div', { className: 'flex items-center gap-3 mt-4' },
          e(Button, { variant: 'primary', onClick: save }, 'Save profile'),
          saved ? e('span', { className: 'text-dim font-mono text-xs' }, 'Saved ' + saved.slice(0, 19)) : null
        ),
        e('p', { className: 'text-faint text-xs mt-3' },
          'Saved to localStorage key ', e('code', null, PROFILE_KEY), '. Hub v2 is read-only otherwise; this profile is the single write.')
        ,
        e('p', { className: 'text-faint text-xs mt-1' },
          'Persisted to disk via aigovclaw.hub.v2.cli dump-profile ~/.hermes/memory/aigovclaw/hub-v2-profile.json')
      )
    );
  }

  // ------------------------------------------------------------------
  // Dashboard (ungrouped top-of-nav)
  // ------------------------------------------------------------------

  function Dashboard(props) {
    var risk = DATA.risk || { by_tier: {}, total: 0 };
    var soa = DATA.soa || { by_status: {} };
    var nc = DATA.nonconformity || { open: 0, in_progress: 0, closed: 0 };
    var kpi = DATA.kpi || { breaches: 0, total: 0 };
    return e('div', null,
      e(PanelHeader, {
        crumbs: ['Home', 'Dashboard'],
        title: 'Dashboard',
        desc: 'Composite AIMS posture. Open a panel for detail.',
      }),
      e('div', { className: 'grid grid-cols-4 gap-3 mb-4' },
        e('div', { className: 'tile' },
          e('span', { className: 'count accent' }, String(risk.total || 0)),
          e('span', { className: 'label' }, 'Risks tracked')),
        e('div', { className: 'tile' },
          e('span', { className: 'count warn' }, String(nc.open || 0)),
          e('span', { className: 'label' }, 'Open nonconformities')),
        e('div', { className: 'tile' },
          e('span', { className: 'count' }, String(kpi.total || 0)),
          e('span', { className: 'label' }, 'KPIs tracked')),
        e('div', { className: 'tile' },
          e('span', { className: 'count ' + ((kpi.breaches || 0) > 0 ? 'danger' : 'ok') }, String(kpi.breaches || 0)),
          e('span', { className: 'label' }, 'Threshold breaches'))
      ),
      e(Card, { panelId: 'dashboard' },
        e(CardHeader, null, e(CardTitle, null, 'Framework gap'), e(CardDescription, null, 'Coverage across ISO 42001, NIST AI RMF, EU AI Act.')),
        ((DATA.gap && DATA.gap.frameworks) || []).map(function(fw, i) {
          return e(CoverageBar, { key: i, label: fw.label, pct: fw.pct });
        })
      )
    );
  }

  // ------------------------------------------------------------------
  // Command palette
  // ------------------------------------------------------------------

  function CommandPalette(props) {
    var open = props.open;
    var onClose = props.onClose;
    var nav = props.navigate;
    var _q = useState('');
    var q = _q[0]; var setQ = _q[1];
    var searchRef = useRef(null);
    useEffect(function() {
      if (open && searchRef.current) searchRef.current.focus();
      if (!open) setQ('');
    }, [open]);

    if (!open) return null;

    var all = [];
    (CATALOG.groups || []).forEach(function(g) {
      (g.items || []).forEach(function(i) {
        all.push({ id: i.id, label: i.label, group: g.label });
      });
    });
    ['dashboard', 'certification', 'tasks'].forEach(function(k) {
      all.push({ id: k, label: k.charAt(0).toUpperCase() + k.slice(1), group: '' });
    });

    var ql = q.toLowerCase();
    var results = all.filter(function(r) {
      return !q || r.label.toLowerCase().indexOf(ql) !== -1 || r.group.toLowerCase().indexOf(ql) !== -1;
    }).slice(0, 30);

    function select(id) { onClose(); nav(id); }

    return e('div', null,
      e('div', {
        className: 'dialog-overlay',
        onClick: onClose,
        style: { background: 'rgba(10,25,41,0.55)' },
      }),
      e('div', { className: 'cmdk', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Command palette' },
        e('input', {
          ref: searchRef,
          type: 'text',
          placeholder: 'Search citations, plugins, panels ...',
          value: q,
          onChange: function(ev) { setQ(ev.target.value); },
          onKeyDown: function(ev) {
            if (ev.key === 'Escape') onClose();
            if (ev.key === 'Enter' && results[0]) select(results[0].id);
          },
          'aria-label': 'Command search',
        }),
        e('div', { className: 'list' },
          results.length === 0
            ? e('p', { className: 'text-dim p-2 text-sm' }, 'No results.')
            : results.map(function(r) {
                return e('div', {
                  key: r.id,
                  className: 'list-item',
                  role: 'option',
                  onClick: function() { select(r.id); },
                },
                  e('span', { className: 'text-text' }, r.label),
                  r.group ? e('span', { className: 'text-faint ml-2 font-mono text-xs' }, r.group) : null
                );
              })
        ),
        e('div', { className: 'px-3 py-2 border-t font-mono text-xs text-faint' },
          'Enter to open. Esc to close. ', e('kbd', null, '/'), ' anywhere to reopen.')
      )
    );
  }

  // ------------------------------------------------------------------
  // Empty-state welcome page
  // ------------------------------------------------------------------

  function WelcomePage(props) {
    return e('div', { className: 'p-6 max-w-screen mx-auto' },
      e('div', { className: 'mb-4' },
        e('span', { className: 'font-display text-xs uppercase tracking-wider text-accent' }, 'AIGovClaw Hub v2'),
        e('h1', { className: 'font-display font-semibold text-3xl mt-1' }, 'No evidence yet.')
      ),
      e(Alert, { tone: 'info' },
        'The evidence store is empty: ',
        e('span', { className: 'mono' }, DATA.evidence_path || '(unspecified)')
      ),
      e(Card, { panelId: 'welcome' },
        e(CardHeader, null,
          e(CardTitle, null, 'Start with cascade intake'),
          e(CardDescription, null, 'Capture organization posture once. Downstream panels filter accordingly.')),
        e('ol', { className: 'text-dim text-sm pl-4' },
          e('li', null, 'Open Cascade intake and enter your industry, jurisdictions, systems, and risk appetite.'),
          e('li', null, 'Run a plugin. For example: hermes run aigovops.risk-register-builder'),
          e('li', null, 'Regenerate this hub. All 30+ panels light up automatically.')
        ),
        e('div', { className: 'mt-4' },
          e(Button, {
            variant: 'primary',
            onClick: function() { window.location.hash = '#/cascade-intake'; },
          }, 'Open cascade intake'))
      )
    );
  }

  // ------------------------------------------------------------------
  // App
  // ------------------------------------------------------------------

  function App() {
    var _r = useHashRoute();
    var route = _r[0]; var navigate = _r[1];

    var _collapsed = useState(safeGet(SIDEBAR_KEY, {}));
    var collapsed = _collapsed[0]; var setCollapsed = _collapsed[1];

    var _j = useState(safeGet(JURIS_KEY, null) || 'global');
    var j = _j[0]; var setJ = _j[1];

    var _cmd = useState(false);
    var cmdOpen = _cmd[0]; var setCmdOpen = _cmd[1];

    // Keyboard shortcuts.
    useEffect(function() {
      function onKey(ev) {
        if (ev.target && (ev.target.tagName === 'INPUT' || ev.target.tagName === 'TEXTAREA')) {
          if (ev.key === 'Escape') setCmdOpen(false);
          return;
        }
        if (ev.key === '/') { ev.preventDefault(); setCmdOpen(true); }
        else if (ev.key === 'Escape') setCmdOpen(false);
      }
      window.addEventListener('keydown', onKey);
      return function() { window.removeEventListener('keydown', onKey); };
    }, []);

    // Jurisdiction filter (visual indicator only; panels read DATA freely).
    useEffect(function() {
      document.body.setAttribute('data-jurisdiction', j);
    }, [j]);

    if (!DATA.has_any_artifacts && route === 'dashboard') {
      // Welcome page replaces dashboard when the store is empty.
      return e('div', { className: 'app-shell' },
        e(Sidebar, { collapsed: collapsed, setCollapsed: setCollapsed, route: route, navigate: navigate }),
        e('div', { className: 'main-col' },
          e(ActionBanner, { data: DATA.action_required }),
          e(WelcomePage, null)
        )
      );
    }

    return e('div', { className: 'app-shell' },
      e('a', { className: 'skip-link', href: '#content' }, 'Skip to content'),
      e(Sidebar, { collapsed: collapsed, setCollapsed: setCollapsed, route: route, navigate: navigate }),
      e('div', { className: 'main-col' },
        e(ActionBanner, { data: DATA.action_required }),
        e('header', { className: 'topbar' },
          e('div', { className: 'flex flex-col' },
            e('span', { className: 'font-display text-xs uppercase tracking-wider text-accent' }, 'AIGovClaw Hub v2'),
            e('span', { className: 'font-mono text-xs text-faint' }, DATA.generated_at || '')
          ),
          e('div', { className: 'flex-1' }),
          e(JurisdictionBar, { value: j, onChange: setJ }),
          e(Button, { onClick: function() { setCmdOpen(true); }, title: 'Search (press /)' }, 'Search ', e('kbd', null, '/'))
        ),
        e('main', { id: 'content', className: 'content anim-fade-in-up' },
          e(Panel, { id: route })
        )
      ),
      e(CommandPalette, { open: cmdOpen, onClose: function() { setCmdOpen(false); }, navigate: navigate })
    );
  }

  var container = document.getElementById('root');
  if (ReactDOM.createRoot) {
    ReactDOM.createRoot(container).render(e(App));
  } else {
    ReactDOM.render(e(App), container);
  }
})();
"""


# --------------------------------------------------------------------------
# Top-level HTML template
# --------------------------------------------------------------------------

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="aigovclaw-hub/v2">
<meta name="color-scheme" content="dark">
<title>AIGovClaw Hub v2. Practitioner dashboard.</title>
<style>{tailwind_css}</style>
</head>
<body>
<div id="root"></div>
<script>/* React 18 UMD */
{react_umd}
</script>
<script>/* ReactDOM 18 UMD */
{react_dom_umd}
</script>
<script type="application/json" id="__AIGOVCLAW_HUB_V2_DATA__">
{data_json}
</script>
<script>
(function() {{
  var el = document.getElementById('__AIGOVCLAW_HUB_V2_DATA__');
  if (el) {{
    try {{ window.__AIGOVCLAW_HUB_V2_DATA__ = JSON.parse(el.textContent); }}
    catch (err) {{ window.__AIGOVCLAW_HUB_V2_DATA__ = {{}}; }}
  }}
}})();
</script>
<script>
{app_js}
</script>
</body>
</html>
"""


VENDOR_MISSING_MESSAGE = (
    "FATAL: AIGovClaw Hub v2 requires vendored React bundles.\n"
    "Drop the following files into hub/v2/vendor/ and retry:\n"
    "  - hub/v2/vendor/react.production.min.js\n"
    "  - hub/v2/vendor/react-dom.production.min.js\n"
    "Source: https://unpkg.com/react@18/umd/react.production.min.js\n"
    "Source: https://unpkg.com/react-dom@18/umd/react-dom.production.min.js\n"
    "Download offline, verify the contents, commit the files.\n"
    "See hub/v2/vendor/README.md for details.\n"
    "No network fetch is performed by the generator."
)
