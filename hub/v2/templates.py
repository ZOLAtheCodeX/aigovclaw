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

/* Command Center. */
.health-strip {
  display: flex; gap: 8px; flex-wrap: wrap;
  padding: 8px 16px;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
}
.chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px;
  background: var(--surface-3);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 12px;
  font-family: var(--font-display);
  cursor: pointer;
}
.chip.ok { border-color: var(--success-dim); color: var(--success); }
.chip.warn { border-color: var(--warning-dim); color: var(--warning); }
.chip.danger { border-color: var(--danger-dim); color: var(--danger); }
.chip.accent { border-color: var(--accent-dim); color: var(--accent); }
.chip .sym { font-family: var(--font-mono); }

.quick-actions {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}
.quick-action {
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-2);
}
.task-queue .task-section { margin-bottom: 12px; }
.task-section-header {
  cursor: pointer;
  font-family: var(--font-display);
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-dim);
  padding: 4px 0;
}
.task-section-header .chev { margin-left: 6px; color: var(--text-faint); }
.task-row {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  margin-bottom: 6px;
}
.status-dot {
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--border-2);
  display: inline-block;
}
.status-dot.pulse {
  background: var(--success);
  animation: pulse 1.2s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.4; }
}
.stdout-tail {
  margin-top: 8px;
  padding: 8px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  max-height: 220px;
  overflow: auto;
  white-space: pre-wrap;
}
.approval-queue .approval-card {
  padding: 12px;
  border: 1px solid var(--warning-dim);
  background: var(--surface-2);
  border-radius: var(--radius-sm);
  margin-bottom: 8px;
}
.activity-log ul { list-style: none; padding: 0; }
.activity-row {
  display: flex; align-items: center; gap: 8px;
  padding: 4px 0;
  border-bottom: 1px solid var(--border);
}
.activity-row:last-child { border-bottom: none; }

.executive-view .exec-hero { margin-bottom: 16px; }
.executive-view .exec-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}
.executive-view .exec-stat {
  padding: 14px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  text-align: center;
}
.executive-view .exec-stat .count {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 700;
}
.executive-view .exec-stat .count.danger { color: var(--danger); }
.executive-view .exec-stat .count.warn   { color: var(--warning); }
.executive-view .exec-stat .count.ok     { color: var(--success); }
.executive-view .exec-stat .count.accent { color: var(--accent); }
.executive-view .exec-stat .label {
  font-family: var(--font-display);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-dim);
  margin-top: 4px;
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

  // ------------------------------------------------------------------
  // Command Center components
  //
  // The Command Center turns Hub v2 from a static dashboard into a live
  // operations surface. Components in this block talk to the local
  // hub/v2_server HTTP API via fetch():
  //
  //   GET  /api/health     polled every 10s, drives HealthStrip
  //   GET  /api/tasks      polled every 2s,  drives TaskQueue
  //   GET  /api/approvals  polled with tasks, drives ApprovalQueue
  //   GET  /api/commands   loaded once,      drives QuickActions
  //   POST /api/tasks      enqueue a task
  //   POST /api/tasks/:id/pause|resume|cancel
  //   POST /api/approvals/:id/approve|reject
  //
  // The server is optional. When it is not reachable (e.g. the hub was
  // generated as a static file and opened directly), every component
  // degrades to a quiet "server offline" placeholder.
  // ------------------------------------------------------------------

  var API_BASE = (window.__AIGOVCLAW_HUB_V2_API_BASE__ || '');
  var EXEC_VIEW_KEY = 'aigovclaw.hub.v2.executiveView';

  function apiFetch(path, options) {
    options = options || {};
    var url = API_BASE + path;
    var init = { method: options.method || 'GET', headers: { 'Content-Type': 'application/json' } };
    if (options.body) init.body = JSON.stringify(options.body);
    return fetch(url, init).then(function(resp) {
      if (!resp.ok) {
        return resp.text().then(function(t) {
          var err = new Error('HTTP ' + resp.status + ': ' + t);
          err.status = resp.status;
          throw err;
        });
      }
      return resp.json();
    });
  }

  function useInterval(callback, ms) {
    var ref = useRef(callback);
    useEffect(function() { ref.current = callback; }, [callback]);
    useEffect(function() {
      if (ms == null) return;
      var tick = function() { try { ref.current(); } catch (e) {} };
      tick();
      var id = setInterval(tick, ms);
      return function() { clearInterval(id); };
    }, [ms]);
  }

  function useServerState() {
    // Owns health + tasks + approvals + commands, polled on intervals.
    var _s = useState({
      health: null, tasks: [], approvals: [], commands: [],
      serverOnline: null, lastError: null,
    });
    var s = _s[0]; var setS = _s[1];

    function merge(part) { setS(function(prev) { return Object.assign({}, prev, part); }); }

    useEffect(function() {
      apiFetch('/api/commands').then(function(d) {
        merge({ commands: d.commands || [], serverOnline: true });
      }).catch(function(err) {
        merge({ serverOnline: false, lastError: String(err.message || err) });
      });
    }, []);

    useInterval(function() {
      Promise.all([apiFetch('/api/tasks?limit=50'), apiFetch('/api/approvals')])
        .then(function(res) {
          merge({
            tasks: (res[0] && res[0].tasks) || [],
            approvals: (res[1] && res[1].approvals) || [],
            serverOnline: true,
          });
        })
        .catch(function(err) { merge({ serverOnline: false, lastError: String(err.message || err) }); });
    }, 2000);

    useInterval(function() {
      apiFetch('/api/health')
        .then(function(h) { merge({ health: h, serverOnline: true }); })
        .catch(function(err) { merge({ serverOnline: false, lastError: String(err.message || err) }); });
    }, 10000);

    return s;
  }

  function HealthStrip(props) {
    var s = props.server || {};
    var h = s.health || {};
    var tasks = s.tasks || [];
    var running = tasks.filter(function(t) { return t.status === 'running' || t.status === 'paused'; });
    var lastRun = tasks.filter(function(t) { return ['succeeded','failed','cancelled','interrupted'].indexOf(t.status) >= 0; })[0];
    function Chip(props) {
      return e('button', {
        type: 'button',
        className: cx('chip', props.tone || ''),
        onClick: props.onClick,
        title: props.title,
      }, props.children);
    }
    if (s.serverOnline === false) {
      return e('div', { className: 'health-strip', role: 'status', 'data-health-strip': '1' },
        e(Chip, { tone: 'warn', title: 'Command-center server is not reachable. Live data disabled.' }, 'Server offline')
      );
    }
    var warnTone = (h.warning_count || 0) > 0 ? 'warn' : 'ok';
    return e('div', { className: 'health-strip', role: 'status', 'data-health-strip': '1' },
      e(Chip, { tone: 'ok', title: 'Plugin count (sibling aigovops repo)', onClick: function() { window.location.hash = '#/command-center'; } },
        e('span', { className: 'sym' }, '\u2713'), ' ', String(h.plugin_count || 0), ' plugins'),
      e(Chip, { tone: warnTone, title: 'Open warnings across latest artifacts', onClick: function() { window.location.hash = '#/command-center'; } },
        e('span', { className: 'sym' }, '\u22ef'), ' ', String(h.warning_count || 0), ' warnings'),
      e(Chip, { tone: h.bundle_signed ? 'ok' : '', title: 'Latest bundle signature state', onClick: function() { window.location.hash = '#/evidence-bundle-packager'; } },
        e('span', { className: 'sym' }, h.bundle_signed ? '\u2713' : '\u00b7'), ' ', h.bundle_signed ? 'bundle signed' : 'bundle unsigned'),
      e(Chip, { tone: '', title: 'Most recent completed task', onClick: function() { window.location.hash = '#/command-center'; } },
        e('span', { className: 'sym' }, '\u21bb'), ' last run: ', (lastRun && (lastRun.ended_at || lastRun.started_at)) || (h.last_run_at || 'none')),
      running.length > 0
        ? e(Chip, { tone: 'accent', title: running.length + ' running task(s)', onClick: function() { window.location.hash = '#/command-center'; } },
            String(running.length), ' running')
        : null
    );
  }

  function QuickActions(props) {
    var commands = (props.server && props.server.commands) || [];
    if (commands.length === 0) {
      return e('p', { className: 'text-dim text-sm' }, 'No commands available. Server offline or registry empty.');
    }
    function onRun(cmd) {
      // Minimal args prompt for the handful of commands that need input.
      var args = {};
      (cmd.args_schema || []).forEach(function(a) {
        if (!a.required) return;
        var v = window.prompt('Enter value for ' + a.name + (a.help ? ' (' + a.help + ')' : ''));
        if (v != null) args[a.name] = v;
      });
      apiFetch('/api/tasks', { method: 'POST', body: { command: cmd.id, args: args } })
        .then(function() { /* polling will pick it up */ })
        .catch(function(err) { alert('Failed to enqueue: ' + err.message); });
    }
    return e('div', { className: 'quick-actions', 'data-quick-actions': '1' },
      commands.map(function(cmd) {
        return e('div', { key: cmd.id, className: 'quick-action' },
          e('div', { className: 'flex items-center justify-between' },
            e('span', { className: 'font-display font-semibold text-sm' }, cmd.display_name),
            e(Badge, { tone: cmd.category === 'pipeline' ? 'accent' : cmd.category === 'bundle' ? 'info' : cmd.category === 'diagnostic' ? 'ok' : '' }, cmd.category)
          ),
          e('p', { className: 'text-dim text-xs mt-1', title: cmd.description }, cmd.description),
          cmd.requires_approval ? e(Badge, { tone: 'warn' }, 'Needs approval') : null,
          e('div', { className: 'mt-2' },
            e(Button, { variant: 'primary', onClick: function() { onRun(cmd); } }, 'Run')
          )
        );
      })
    );
  }

  function TaskRow(props) {
    var t = props.task;
    var _open = useState(false); var open = _open[0]; var setOpen = _open[1];
    var tone = t.status === 'running' ? 'accent' : t.status === 'paused' ? 'warn' : t.status === 'succeeded' ? 'ok' : t.status === 'failed' || t.status === 'cancelled' ? 'danger' : '';
    function act(action) {
      apiFetch('/api/tasks/' + t.task_id + '/' + action, { method: 'POST' })
        .catch(function(err) { alert(action + ' failed: ' + err.message); });
    }
    var elapsed = '';
    if (t.started_at) {
      try {
        var d0 = new Date(t.started_at).getTime();
        var d1 = t.ended_at ? new Date(t.ended_at).getTime() : Date.now();
        elapsed = Math.max(0, Math.round((d1 - d0) / 1000)) + 's';
      } catch (e) { /* ignore */ }
    }
    return e('div', { className: 'task-row', 'data-task-id': t.task_id },
      e('div', { className: 'flex items-center gap-3' },
        e('span', { className: cx('status-dot', tone === 'accent' ? 'pulse' : '') }),
        e('span', { className: 'font-display text-sm flex-1' }, t.command + ' ', e('span', { className: 'mono text-faint text-xs' }, t.task_id.slice(0, 8))),
        e(Badge, { tone: tone }, t.status),
        elapsed ? e('span', { className: 'mono text-xs text-dim' }, elapsed) : null,
        t.status === 'running' ? e(Button, { onClick: function() { act('pause'); } }, 'Pause') : null,
        t.status === 'paused' ? e(Button, { onClick: function() { act('resume'); } }, 'Resume') : null,
        (t.status === 'running' || t.status === 'paused' || t.status === 'queued')
          ? e(Button, { onClick: function() { act('cancel'); } }, 'Cancel') : null,
        e(Button, { onClick: function() { setOpen(!open); } }, open ? 'Hide output' : 'Show output')
      ),
      open ? e('pre', { className: 'stdout-tail mono text-xs' },
        (t.stdout_tail || []).slice(-20).join('\n') || '(no output captured yet)'
      ) : null
    );
  }

  function TaskQueue(props) {
    var tasks = (props.server && props.server.tasks) || [];
    var running = tasks.filter(function(t) { return t.status === 'running' || t.status === 'paused'; });
    var queued  = tasks.filter(function(t) { return t.status === 'queued' || t.status === 'awaiting-approval'; });
    var done    = tasks.filter(function(t) { return ['succeeded','failed','cancelled','interrupted'].indexOf(t.status) >= 0; }).slice(0, 20);

    function Section(props) {
      var _c = useState(props.defaultOpen !== false); var openSec = _c[0]; var setOpenSec = _c[1];
      return e('section', { className: 'task-section' },
        e('h4', {
          className: 'task-section-header',
          role: 'button',
          tabIndex: 0,
          onClick: function() { setOpenSec(!openSec); },
        }, props.title, ' ', e('span', { className: 'badge' }, String((props.items || []).length)), e('span', { className: 'chev' }, openSec ? '-' : '+')),
        openSec ? (
          (props.items && props.items.length)
            ? e('div', null, props.items.map(function(t) { return e(TaskRow, { key: t.task_id, task: t }); }))
            : e('p', { className: 'text-dim text-xs' }, props.empty || 'Nothing here.')
        ) : null
      );
    }

    return e('div', { className: 'task-queue', 'data-task-queue': '1' },
      e(Section, { title: 'Running', items: running, empty: 'No tasks running.', defaultOpen: true }),
      e(Section, { title: 'Queued / awaiting approval', items: queued, empty: 'Queue is empty.', defaultOpen: true }),
      e(Section, { title: 'Recently completed', items: done, empty: 'No completed tasks yet.', defaultOpen: false })
    );
  }

  function ApprovalQueuePanel(props) {
    var approvals = (props.server && props.server.approvals) || [];
    if (approvals.length === 0) {
      return e('p', { className: 'text-dim text-sm', 'data-approval-queue': 'empty' }, 'No approvals pending.');
    }
    function decide(id, action) {
      apiFetch('/api/approvals/' + id + '/' + action, { method: 'POST', body: action === 'reject' ? { reason: 'rejected via command center' } : {} })
        .catch(function(err) { alert(action + ' failed: ' + err.message); });
    }
    return e('div', { className: 'approval-queue', 'data-approval-queue': '1' },
      approvals.map(function(ap) {
        return e('div', { key: ap.task_id, className: 'approval-card' },
          e('div', { className: 'flex items-center justify-between' },
            e('span', { className: 'font-display font-semibold text-sm' }, ap.command),
            e(Badge, { tone: 'warn' }, 'awaiting approval')
          ),
          e('pre', { className: 'mono text-xs text-dim' }, JSON.stringify(ap.args || {}, null, 2)),
          e('div', { className: 'flex gap-2 mt-2' },
            e(Button, { variant: 'primary', onClick: function() { decide(ap.task_id, 'approve'); } }, 'Approve'),
            e(Button, { onClick: function() { decide(ap.task_id, 'reject'); } }, 'Reject')
          )
        );
      })
    );
  }

  function ActivityLog(props) {
    var tasks = (props.server && props.server.tasks) || [];
    var events = tasks.slice(0, 100).map(function(t) {
      return {
        id: t.task_id,
        at: t.ended_at || t.started_at || t.queued_at,
        label: t.command,
        status: t.status,
        summary: t.summary,
      };
    });
    events.sort(function(a, b) { return (b.at || '').localeCompare(a.at || ''); });
    return e('div', { className: 'activity-log', 'data-activity-log': '1' },
      events.length === 0
        ? e('p', { className: 'text-dim text-sm' }, 'No activity yet.')
        : e('ul', { className: 'text-sm' }, events.map(function(ev) {
            return e('li', { key: ev.id, className: 'activity-row' },
              e('span', { className: 'mono text-xs text-faint', style: { minWidth: 180, display: 'inline-block' } }, ev.at || '-'),
              e('span', { className: 'mr-2' }, ev.label),
              e(Badge, { tone: ev.status === 'succeeded' ? 'ok' : ev.status === 'failed' ? 'danger' : '' }, ev.status),
              ev.summary ? e('span', { className: 'text-dim text-xs ml-2' }, ev.summary) : null
            );
          }))
    );
  }

  function CommandCenterPanel(props) {
    var meta = (CATALOG.panels || {})['command-center'] || {};
    var server = props.server;
    return e('div', { 'data-command-center': '1' },
      e(PanelHeader, {
        crumbs: ['Home', 'COMMAND CENTER', meta.title || 'Command center'],
        title: meta.title || 'Command center',
        desc: meta.description || '',
      }),
      e(HealthStrip, { server: server }),
      e(Card, { panelId: 'command-center' },
        e(CardHeader, null,
          e(CardTitle, null, 'Quick actions'),
          e(CardDescription, null, 'Click a button to enqueue a task. Destructive operations require approval.')
        ),
        e(QuickActions, { server: server })
      ),
      e(Card, { panelId: 'command-center-queue' },
        e(CardHeader, null,
          e(CardTitle, null, 'Task queue'),
          e(CardDescription, null, 'Auto-refresh every 2 seconds. Pause, resume, or cancel running tasks.')
        ),
        e(TaskQueue, { server: server })
      ),
      e(Card, { panelId: 'command-center-approvals' },
        e(CardHeader, null,
          e(CardTitle, null, 'Pending approvals'),
          e(CardDescription, null, 'Tasks flagged destructive or external wait here until a human decides.')
        ),
        e(ApprovalQueuePanel, { server: server })
      ),
      e(Card, { panelId: 'command-center-activity' },
        e(CardHeader, null,
          e(CardTitle, null, 'Activity log'),
          e(CardDescription, null, 'Reverse-chronological feed of tasks and decisions. Limit 100.')
        ),
        e(ActivityLog, { server: server })
      )
    );
  }

  function ExecutiveView(props) {
    var server = props.server;
    var h = (server && server.health) || {};
    var juris = h.jurisdictions || {};
    var tasks = (server && server.tasks) || [];
    var openApprovals = ((server && server.approvals) || []).length;
    var openWarnings = h.warning_count || 0;
    var running = tasks.filter(function(t) { return t.status === 'running'; }).length;
    function StatCard(props) {
      return e('div', { className: 'exec-stat' },
        e('div', { className: cx('count', props.tone || '') }, String(props.value)),
        e('div', { className: 'label' }, props.label)
      );
    }
    var frameworks = [
      { id: 'iso-42001', label: 'ISO 42001',    fallback: 'unknown' },
      { id: 'eu-ai-act', label: 'EU AI Act',     fallback: 'unknown' },
      { id: 'nist-ai-rmf', label: 'NIST AI RMF', fallback: 'unknown' },
      { id: 'uk-atrs',   label: 'UK ATRS',       fallback: 'unknown' },
      { id: 'nyc-ll144', label: 'NYC LL 144',    fallback: 'unknown' },
    ];
    return e('div', { className: 'executive-view', 'data-executive-view': '1' },
      e('header', { className: 'exec-hero' },
        e('div', { className: 'text-xs uppercase tracking-wider text-accent font-display' }, 'AI governance posture'),
        e('h1', { className: 'font-display text-2xl font-bold' }, 'Your posture at a glance'),
        e('p', { className: 'text-dim text-sm' }, 'Executive summary. Switch to Operating view for task-level detail.')
      ),
      e('div', { className: 'exec-stats' },
        e(StatCard, { value: (DATA.risk && DATA.risk.by_tier && DATA.risk.by_tier.high) || 0, label: 'High risks', tone: 'danger' }),
        e(StatCard, { value: (DATA.nonconformity && DATA.nonconformity.open) || 0, label: 'Open nonconformities', tone: 'warn' }),
        e(StatCard, { value: openApprovals, label: 'Pending approvals', tone: 'warn' }),
        e(StatCard, { value: openWarnings, label: 'Artifact warnings', tone: 'warn' }),
        e(StatCard, { value: running, label: 'Tasks running', tone: 'accent' }),
        e(StatCard, { value: h.plugin_count || 0, label: 'Plugins available', tone: 'ok' })
      ),
      e(Card, { panelId: 'executive-frameworks' },
        e(CardHeader, null,
          e(CardTitle, null, 'Per-framework readiness')
        ),
        e('div', null, frameworks.map(function(f) {
          var rec = juris[f.id] || {};
          return e('div', { key: f.id, className: 'flex items-center gap-3 mb-2' },
            e('span', { className: 'font-display text-sm', style: { minWidth: 140 } }, f.label),
            e(Badge, { tone: rec.status === 'ready' ? 'ok' : rec.status ? 'warn' : '' }, rec.status || f.fallback)
          );
        }))
      ),
      e(Card, { panelId: 'executive-now' },
        e(CardHeader, null,
          e(CardTitle, null, 'Top five things right now')
        ),
        e('ul', { className: 'text-sm' },
          openApprovals > 0 ? e('li', null, openApprovals + ' pending approval(s). ', e('a', { href: '#/command-center' }, 'Review')) : null,
          openWarnings > 0 ? e('li', null, openWarnings + ' artifact warning(s) in latest run. ', e('a', { href: '#/command-center' }, 'Inspect')) : null,
          !h.bundle_signed ? e('li', null, 'Latest bundle is unsigned. ', e('a', { href: '#/evidence-bundle-packager' }, 'Pack')) : null,
          ((DATA.risk && DATA.risk.by_tier && DATA.risk.by_tier.high) || 0) > 0
            ? e('li', null, 'High risks require treatment. ', e('a', { href: '#/risk-register-builder' }, 'Open register')) : null,
          ((DATA.nonconformity && DATA.nonconformity.open) || 0) > 0
            ? e('li', null, 'Open nonconformities. ', e('a', { href: '#/nonconformity-tracker' }, 'Review')) : null
        )
      )
    );
  }

  // ------------------------------------------------------------------
  // Bespoke-renderer helpers
  // ------------------------------------------------------------------

  function EmptyPanel(props) {
    return e('div', { 'data-empty': '1' },
      e('p', { className: 'text-dim text-sm' }, props.message || 'No artifact data for this panel yet.'),
      props.hint ? e('div', { className: 'bg-surface-2 border rounded p-3 mono text-xs mt-2' }, props.hint) : null
    );
  }

  function latestFor(key) {
    var entry = (DATA.artifacts || {})[key];
    if (!entry || !entry.latest) return null;
    return entry.latest;
  }

  function countFor(key) {
    var entry = (DATA.artifacts || {})[key];
    return (entry && entry.count) || 0;
  }

  function warningsFor(key) {
    var latest = latestFor(key);
    if (!latest) return [];
    var w = latest.warnings;
    return Array.isArray(w) ? w : [];
  }

  function ValidationFromWarnings(props) {
    var warns = warningsFor(props.storeKey);
    if (warns.length === 0) return e(Alert, { tone: 'ok' }, 'No warnings reported in the latest artifact.');
    return e('div', null,
      e('p', { className: 'text-dim text-sm mb-2' }, String(warns.length) + ' warning(s) in latest artifact.'),
      e('ul', { className: 'text-sm' }, warns.slice(0, 50).map(function(w, i) {
        var text = typeof w === 'string' ? w : (w && (w.message || w.text || w.reason)) || JSON.stringify(w);
        return e('li', { key: i, className: 'mb-1 text-dim' }, '- ', text);
      }))
    );
  }

  function GuidanceSkill(props) {
    var panelMeta = (CATALOG.panels || {})[props.panelId] || {};
    return e('div', null,
      e('p', { className: 'text-dim text-sm mb-3' }, props.purpose || panelMeta.description || 'Plugin guidance.'),
      panelMeta.plugin ? e('div', { className: 'mb-2' },
        e('span', { className: 'text-faint text-xs uppercase tracking-wide font-display' }, 'Plugin'),
        e('div', { className: 'mono text-sm mt-1' }, panelMeta.plugin)
      ) : null,
      panelMeta.skill ? e('div', { className: 'mb-2' },
        e('span', { className: 'text-faint text-xs uppercase tracking-wide font-display' }, 'Skill source'),
        e('div', { className: 'mono text-sm mt-1' }, panelMeta.skill)
      ) : null,
      props.citations && props.citations.length
        ? e('div', { className: 'mb-2' },
            e('span', { className: 'text-faint text-xs uppercase tracking-wide font-display' }, 'Key citations'),
            e('ul', { className: 'text-sm mt-1' }, props.citations.map(function(c, i) {
              return e('li', { key: i, className: 'text-dim mono' }, '- ', c);
            })))
        : null,
      panelMeta.frameworks && panelMeta.frameworks.length
        ? e('div', { className: 'mt-3 flex flex-wrap gap-2' },
            panelMeta.frameworks.map(function(f, i) { return e(Badge, { key: i, tone: 'info' }, f); }))
        : null
    );
  }

  function SimpleTable(props) {
    var cols = props.cols || [];
    var rows = props.rows || [];
    return e('div', { className: 'overflow-x-auto' },
      e('table', null,
        e('thead', null, e('tr', null, cols.map(function(c, i) { return e('th', { key: i }, c.label); }))),
        e('tbody', null, rows.slice(0, props.max || 100).map(function(r, i) {
          return e('tr', { key: i }, cols.map(function(c, j) {
            var val = c.render ? c.render(r) : (r[c.key] == null ? '-' : String(r[c.key]));
            return e('td', { key: j, className: c.mono ? 'mono' : '' }, val);
          }));
        }))
      )
    );
  }

  // ------------------------------------------------------------------
  // Bespoke renderer triples
  // Every renderer is guarded with ?. / || fallbacks; missing data
  // resolves to EmptyPanel. Each component is tagged with a data-panel
  // attribute on its outermost wrapper for tests.
  // ------------------------------------------------------------------

  // CASCADE group

  function GuidanceRegFeed() {
    return e(GuidanceSkill, { panelId: 'framework-monitor',
      purpose: 'Continuous monitor of authoritative framework URLs. Flags changes, new clauses, retirements.',
      citations: ['ISO/IEC 42001:2023, Clause 4.1', 'EU AI Act, Article 112'] });
  }
  function ArtifactsRegFeed() {
    var latest = latestFor('framework-monitor');
    if (!latest) return e(EmptyPanel, { message: 'No regulatory feed runs recorded yet.', hint: 'workflows/framework-monitor emits detections under ~/.hermes/memory/aigovclaw/framework-monitor/' });
    var changes = latest.changes || latest.detections || [];
    return e('div', { 'data-panel': 'regulatory-feed' },
      e('p', { className: 'text-dim text-sm mb-2' }, String(changes.length) + ' changes detected at last run.'),
      e(SimpleTable, { cols: [
        { key: 'framework', label: 'Framework' },
        { key: 'url', label: 'URL', mono: true },
        { key: 'detected_at', label: 'Detected', mono: true },
        { key: 'change_type', label: 'Change' },
      ], rows: changes })
    );
  }

  function GuidanceApplicability() {
    return e(GuidanceSkill, { panelId: 'applicability-checker',
      purpose: 'Per-system jurisdiction applicability matrix. Cascade downstream filters from this output.',
      citations: ['EU AI Act, Article 2', 'EU AI Act, Article 113', 'Colorado SB 205, Section 6-1-1701', 'NYC LL144, Section 20-871'] });
  }
  function ArtifactsApplicability() {
    var latest = latestFor('applicability-checker');
    if (!latest) return e(EmptyPanel, { message: 'No applicability assessment artifacts.' });
    var matrix = latest.regulatory_applicability_matrix || latest.matrix || latest.systems || [];
    return e('div', { 'data-panel': 'applicability' },
      e('p', { className: 'text-dim text-sm mb-2' }, 'Applicability matrix for ' + (matrix.length || 0) + ' systems.'),
      e(SimpleTable, { cols: [
        { key: 'system_id', label: 'System', mono: true },
        { key: 'eu_ai_act', label: 'EU', render: function(r) { return e(Badge, { tone: r.eu_ai_act ? 'accent' : '' }, r.eu_ai_act || r.eu_tier || '-'); } },
        { key: 'uk_atrs', label: 'UK', render: function(r) { return e(Badge, { tone: r.uk_atrs ? 'info' : '' }, r.uk_atrs || '-'); } },
        { key: 'colorado', label: 'CO', render: function(r) { return e(Badge, { tone: r.colorado ? 'warn' : '' }, r.colorado || '-'); } },
        { key: 'nyc_ll144', label: 'NYC', render: function(r) { return e(Badge, { tone: r.nyc_ll144 ? 'warn' : '' }, r.nyc_ll144 || '-'); } },
      ], rows: matrix })
    );
  }

  // DISCOVERY group

  function GuidanceGapExplorer() {
    return e(GuidanceSkill, { panelId: 'gap-explorer',
      purpose: 'Unified gap navigator across gap-assessment coverage and crosswalk no-mapping entries.',
      citations: ['ISO/IEC 42001:2023, Clause 6.1.1', 'NIST AI RMF GOVERN 1.1'] });
  }
  function ArtifactsGapExplorer() {
    var gap = DATA.gap || { frameworks: [] };
    var cw = (DATA.crosswalk && DATA.crosswalk.mappings) || [];
    var nomap = cw.filter(function(m) { return (m.relationship || '').toLowerCase().indexOf('no-mapping') !== -1 || (m.relationship || '').toLowerCase() === 'none'; });
    if ((gap.frameworks || []).length === 0 && nomap.length === 0) {
      return e(EmptyPanel, { message: 'No gap-assessment artifacts and no no-mapping crosswalk entries.' });
    }
    return e('div', { 'data-panel': 'gap-explorer' },
      e('h3', { className: 'font-display text-sm mb-2' }, 'Framework coverage'),
      (gap.frameworks || []).map(function(fw, i) { return e(CoverageBar, { key: i, label: fw.label, pct: fw.pct }); }),
      e('h3', { className: 'font-display text-sm mt-4 mb-2' }, 'No-mapping entries (' + nomap.length + ')'),
      nomap.length === 0
        ? e('p', { className: 'text-dim text-sm' }, 'None.')
        : e(SimpleTable, { cols: [
            { key: 'source_fw', label: 'Source FW' },
            { key: 'source_ref', label: 'Source ref', mono: true },
            { key: 'target_fw', label: 'Target FW' },
            { key: 'relationship', label: 'Relationship' },
          ], rows: nomap, max: 50 })
    );
  }

  function GuidanceCitationSearch() {
    return e(GuidanceSkill, { panelId: 'citation-search',
      purpose: 'Client-side full-text search across every citation emitted by any plugin artifact. No backend.',
      citations: ['See STYLE.md for citation format'] });
  }
  function ArtifactsCitationSearch() {
    var _q = useState('');
    var q = _q[0]; var setQ = _q[1];
    var cits = DATA.citations_index || [];
    var ql = q.toLowerCase();
    var rows = useMemo(function() {
      if (!q) return cits.slice(0, 200);
      return cits.filter(function(c) {
        return (c.text || '').toLowerCase().indexOf(ql) !== -1 || (c.source || '').toLowerCase().indexOf(ql) !== -1;
      }).slice(0, 200);
    }, [cits, q]);
    if (cits.length === 0) return e(EmptyPanel, { message: 'No citations indexed. Run a plugin to produce artifacts that include citations.' });
    return e('div', { 'data-panel': 'citation-search' },
      e(Input, { placeholder: 'Search citations', value: q, onChange: function(ev) { setQ(ev.target.value); } }),
      e('p', { className: 'text-faint text-xs mt-2 font-mono' }, 'Showing ' + rows.length + ' of ' + cits.length + ' citations.'),
      e('div', { className: 'overflow-x-auto mt-2' },
        e('table', null,
          e('thead', null, e('tr', null, e('th', null, 'Source plugin'), e('th', null, 'Citation'))),
          e('tbody', null, rows.map(function(r, i) {
            return e('tr', { key: i },
              e('td', null, e(Badge, { tone: 'info' }, r.source)),
              e('td', { className: 'mono' }, r.text)
            );
          }))
        )
      )
    );
  }

  // ASSURANCE group

  function GuidanceAISystems() {
    return e(GuidanceSkill, { panelId: 'ai-system-inventory-maintainer',
      purpose: 'Validated, versioned AI system inventory. Each system carries lifecycle state and applicability.',
      citations: ['ISO/IEC 42001:2023, Annex A, Control A.6.1', 'EU AI Act, Article 11'] });
  }
  function ArtifactsAISystems() {
    var latest = latestFor('ai-system-inventory-maintainer');
    if (!latest) return e(EmptyPanel, { message: 'No AI system inventory recorded yet.' });
    var systems = latest.systems || [];
    var summary = latest.summary || {};
    return e('div', { 'data-panel': 'ai-systems-registry' },
      e(TileRow, { tiles: [
        { count: summary.total_systems || systems.length || 0, label: 'Systems', tone: 'accent' },
        { count: (summary.systems_with_warnings || 0), label: 'With warnings', tone: 'warn' },
        { count: (summary.systems_missing_required_fields || 0), label: 'Missing fields', tone: 'danger' },
      ]}),
      e(SimpleTable, { cols: [
        { key: 'system_id', label: 'System ID', mono: true },
        { key: 'name', label: 'Name' },
        { key: 'lifecycle_state', label: 'Lifecycle', render: function(r) { return e(Badge, { tone: r.lifecycle_state === 'production' ? 'ok' : r.lifecycle_state === 'retired' ? '' : 'info' }, r.lifecycle_state || '-'); } },
        { key: 'risk_tier', label: 'Tier', render: function(r) { return e(Badge, { tone: r.risk_tier === 'high' ? 'danger' : r.risk_tier === 'medium' ? 'warn' : 'ok' }, r.risk_tier || '-'); } },
      ], rows: systems })
    );
  }

  function GuidanceAISIA() {
    return e(GuidanceSkill, { panelId: 'aisia-runner',
      purpose: 'AI System Impact Assessment with FRIA coverage per EU AI Act Article 27.',
      citations: ['ISO/IEC 42001:2023, Clause 6.1.4', 'EU AI Act, Article 27', 'NIST AI RMF MAP 1.x'] });
  }
  function ArtifactsAISIA() {
    var latest = latestFor('aisia');
    if (!latest) return e(EmptyPanel, { message: 'No AISIA artifacts.' });
    var assessments = latest.assessments || latest.systems || [latest];
    var FRIA_ELEMENTS = ['purpose', 'affected_persons', 'risks', 'measures', 'monitoring', 'complaints'];
    return e('div', { 'data-panel': 'aisia-viewer' },
      e('p', { className: 'text-dim text-sm mb-2' }, String(assessments.length) + ' assessment(s).'),
      assessments.slice(0, 20).map(function(a, i) {
        var fria = a.fria || a.fria_coverage || {};
        return e('details', { key: i, className: 'card mb-2', style: { padding: 12 } },
          e('summary', { className: 'font-display font-medium cursor-pointer' },
            (a.system_id || a.name || 'Assessment ' + (i+1)),
            ' ',
            e(Badge, { tone: a.eu_high_risk ? 'danger' : 'info' }, a.eu_high_risk ? 'High risk' : (a.risk_tier || 'assessed'))
          ),
          e('div', { className: 'mt-2 grid grid-cols-3 gap-2' },
            FRIA_ELEMENTS.map(function(k) {
              var present = fria[k] || a[k];
              return e('div', { key: k, className: 'tile' },
                e('span', { className: 'count ' + (present ? 'ok' : 'danger') }, present ? 'yes' : 'no'),
                e('span', { className: 'label' }, k.replace(/_/g, ' '))
              );
            })
          )
        );
      })
    );
  }

  function GuidanceAuditLog() {
    return e(GuidanceSkill, { panelId: 'audit-log-generator',
      purpose: 'Reverse-chronological audit log of governance events with clause tags.',
      citations: ['ISO/IEC 42001:2023, Clause 7.5', 'ISO/IEC 42001:2023, Clause 9.2'] });
  }
  function ArtifactsAuditLog() {
    var latest = latestFor('audit-log-generator');
    if (!latest) return e(EmptyPanel, { message: 'No audit log entries.' });
    var events = latest.events || latest.entries || [];
    events = events.slice().reverse();
    return e('div', { 'data-panel': 'audit-log' },
      e('p', { className: 'text-dim text-sm mb-2' }, String(events.length) + ' events recorded.'),
      e(SimpleTable, { cols: [
        { key: 'timestamp', label: 'When', mono: true },
        { key: 'actor', label: 'Actor' },
        { key: 'action', label: 'Action' },
        { key: 'clause', label: 'Clause', render: function(r) { return r.clause ? e(Badge, { tone: 'info' }, r.clause) : '-'; } },
      ], rows: events, max: 100 })
    );
  }

  function GuidanceMetrics() {
    return e(GuidanceSkill, { panelId: 'metrics-collector',
      purpose: 'KPI dashboard with threshold-breach indicators per NIST MEASURE 2.x.',
      citations: ['NIST AI RMF MEASURE 2.1', 'NIST AI 600-1, Action MS-2.x'] });
  }
  function ArtifactsMetrics() {
    var latest = latestFor('metrics');
    if (!latest) return e(EmptyPanel, { message: 'No metrics artifacts.' });
    var kpis = latest.kpi_records || latest.kpis || [];
    var breaches = latest.threshold_breaches || [];
    var breachIds = {};
    breaches.forEach(function(b) { if (b && b.kpi_id) breachIds[b.kpi_id] = b; });
    return e('div', { 'data-panel': 'metrics' },
      e(TileRow, { tiles: [
        { count: kpis.length, label: 'KPIs tracked', tone: 'accent' },
        { count: breaches.length, label: 'Breaches', tone: breaches.length > 0 ? 'danger' : 'ok' },
      ]}),
      e(SimpleTable, { cols: [
        { key: 'id', label: 'KPI', mono: true },
        { key: 'name', label: 'Name' },
        { key: 'value', label: 'Value', mono: true },
        { key: 'threshold', label: 'Threshold', mono: true },
        { key: 'status', label: 'Status', render: function(r) {
          var breach = breachIds[r.id];
          return e(Badge, { tone: breach ? 'danger' : 'ok' }, breach ? 'Breach' : 'OK');
        } },
      ], rows: kpis })
    );
  }

  function GuidancePMM() {
    return e(GuidanceSkill, { panelId: 'post-market-monitoring',
      purpose: 'Per-dimension cadence and trigger catalogue for post-market monitoring.',
      citations: ['EU AI Act, Article 72', 'ISO/IEC 42001:2023, Clause 9.1', 'NIST AI RMF MANAGE 4.1'] });
  }
  function ArtifactsPMM() {
    var latest = latestFor('post-market-monitoring');
    if (!latest) return e(EmptyPanel, { message: 'No post-market monitoring plan.' });
    var dimensions = latest.dimensions || latest.rows || [];
    var triggers = latest.triggers || latest.trigger_catalogue || [];
    return e('div', { 'data-panel': 'post-market-monitoring' },
      e('h3', { className: 'font-display text-sm mb-2' }, 'Per-dimension cadence (' + dimensions.length + ')'),
      e(SimpleTable, { cols: [
        { key: 'dimension', label: 'Dimension' },
        { key: 'cadence', label: 'Cadence' },
        { key: 'owner', label: 'Owner' },
        { key: 'metric', label: 'Metric', mono: true },
      ], rows: dimensions }),
      e('h3', { className: 'font-display text-sm mt-4 mb-2' }, 'Trigger catalogue (' + triggers.length + ')'),
      e(SimpleTable, { cols: [
        { key: 'trigger', label: 'Trigger' },
        { key: 'threshold', label: 'Threshold', mono: true },
        { key: 'response', label: 'Response' },
      ], rows: triggers })
    );
  }

  function GuidanceRobustness() {
    return e(GuidanceSkill, { panelId: 'robustness-evaluator',
      purpose: 'Point-in-time robustness evaluation with per-dimension pass/fail and adversarial posture.',
      citations: ['EU AI Act, Article 15', 'ISO/IEC 42001:2023, Annex A, Control A.6.2.4', 'NIST AI RMF MEASURE 2.5'] });
  }
  function ArtifactsRobustness() {
    var latest = latestFor('robustness-evaluator');
    if (!latest) return e(EmptyPanel, { message: 'No robustness evaluation recorded.' });
    var dims = latest.dimensions || latest.results || [];
    var posture = latest.adversarial_posture || latest.posture || '-';
    return e('div', { 'data-panel': 'robustness' },
      e('div', { className: 'mb-3' },
        e('span', { className: 'text-faint text-xs uppercase tracking-wide' }, 'Adversarial posture'),
        e('div', { className: 'mt-1' }, e(Badge, { tone: posture === 'mature' ? 'ok' : posture === 'developing' ? 'warn' : 'danger' }, String(posture)))
      ),
      e(SimpleTable, { cols: [
        { key: 'dimension', label: 'Dimension' },
        { key: 'result', label: 'Result', render: function(r) { return e(Badge, { tone: r.result === 'pass' ? 'ok' : r.result === 'fail' ? 'danger' : 'warn' }, r.result || '-'); } },
        { key: 'resilience_level', label: 'Resilience' },
        { key: 'evidence', label: 'Evidence', mono: true },
      ], rows: dims })
    );
  }

  function GuidanceBias() {
    return e(GuidanceSkill, { panelId: 'bias-evaluator',
      purpose: 'Fairness metrics per protected group with jurisdictional rule application.',
      citations: ['NYC LL144, Section 5-303', 'EU AI Act, Article 10(4)', 'Colorado SB 205, Section 6-1-1702(1)'] });
  }
  function ArtifactsBias() {
    var latest = latestFor('bias-evaluator');
    if (!latest) return e(EmptyPanel, { message: 'No bias evaluation artifacts.' });
    var metrics = latest.metrics || latest.results || [];
    var findings = latest.rule_findings || latest.findings || [];
    return e('div', { 'data-panel': 'bias' },
      e('h3', { className: 'font-display text-sm mb-2' }, 'Per-metric results'),
      e(SimpleTable, { cols: [
        { key: 'protected_attribute', label: 'Attribute' },
        { key: 'metric', label: 'Metric' },
        { key: 'value', label: 'Value', mono: true },
        { key: 'reference_group', label: 'Reference' },
      ], rows: metrics }),
      e('h3', { className: 'font-display text-sm mt-4 mb-2' }, 'Jurisdictional rule findings (' + findings.length + ')'),
      e(SimpleTable, { cols: [
        { key: 'jurisdiction', label: 'Jurisdiction' },
        { key: 'rule', label: 'Rule' },
        { key: 'status', label: 'Status', render: function(r) { return e(Badge, { tone: r.status === 'pass' ? 'ok' : 'danger' }, r.status || '-'); } },
        { key: 'detail', label: 'Detail' },
      ], rows: findings })
    );
  }

  function GuidanceBundle() {
    return e(GuidanceSkill, { panelId: 'evidence-bundle-packager',
      purpose: 'Deterministic evidence bundles with optional HMAC-SHA256 signing and provenance chain.',
      citations: ['ISO/IEC 42001:2023, Clause 7.5.3'] });
  }
  function ArtifactsBundle() {
    var latest = latestFor('evidence-bundle-packager');
    if (!latest) return e(EmptyPanel, { message: 'No evidence bundles packaged.' });
    var manifest = latest.manifest || {};
    var artifacts = manifest.artifacts || latest.artifacts_list || [];
    return e('div', { 'data-panel': 'bundle-inspector' },
      e(TileRow, { tiles: [
        { count: artifacts.length, label: 'Artifacts', tone: 'accent' },
        { count: manifest.total_size_bytes || 0, label: 'Bytes' },
        { count: latest.signed ? 1 : 0, label: 'Signed', tone: latest.signed ? 'ok' : 'warn' },
      ]}),
      e('div', { className: 'bg-surface-2 border rounded p-3 mb-3' },
        e('span', { className: 'text-faint text-xs uppercase tracking-wide' }, 'Signature'),
        e('div', { className: 'mono text-xs mt-1 break-all' }, latest.signature || '(unsigned)')
      ),
      e(SimpleTable, { cols: [
        { key: 'path', label: 'Path', mono: true },
        { key: 'sha256', label: 'SHA-256', mono: true, render: function(r) { return (r.sha256 || '').slice(0, 16) + '...'; } },
        { key: 'size', label: 'Size', mono: true },
      ], rows: artifacts })
    );
  }

  function GuidanceCertReady() {
    return e(GuidanceSkill, { panelId: 'certification-readiness',
      purpose: 'Graduated readiness verdict against a target certification with gaps and remediations.',
      citations: ['ISO/IEC 42001:2023 (full standard)'] });
  }
  function ArtifactsCertReady() {
    var latest = latestFor('certification-readiness');
    if (!latest) return e(EmptyPanel, { message: 'No certification readiness assessment yet.' });
    var verdict = latest.verdict || latest.readiness_verdict || 'not-assessed';
    var gaps = latest.gaps || [];
    var remediations = latest.remediations || [];
    var verdictTone = verdict === 'ready' ? 'ok' : verdict === 'ready-with-conditions' ? 'warn' : verdict === 'partially-ready' ? 'warn' : 'danger';
    return e('div', { 'data-panel': 'certification-readiness' },
      e('div', { className: 'card mb-3 text-center' },
        e('span', { className: 'text-faint text-xs uppercase tracking-wide font-display' }, 'Verdict'),
        e('div', { className: 'mt-2' }, e(Badge, { tone: verdictTone }, String(verdict)))
      ),
      e('h3', { className: 'font-display text-sm mb-2' }, 'Gaps (' + gaps.length + ')'),
      e(SimpleTable, { cols: [
        { key: 'clause', label: 'Clause' },
        { key: 'description', label: 'Description' },
        { key: 'severity', label: 'Severity', render: function(r) { return e(Badge, { tone: r.severity === 'blocker' ? 'danger' : r.severity === 'major' ? 'warn' : '' }, r.severity || '-'); } },
      ], rows: gaps }),
      e('h3', { className: 'font-display text-sm mt-4 mb-2' }, 'Remediations (' + remediations.length + ')'),
      e(SimpleTable, { cols: [
        { key: 'action', label: 'Action' },
        { key: 'owner', label: 'Owner' },
        { key: 'target_plugin', label: 'Target plugin', mono: true },
        { key: 'due', label: 'Due', mono: true },
      ], rows: remediations })
    );
  }

  // GOVERNANCE group

  function GuidanceMgmtReview() {
    return e(GuidanceSkill, { panelId: 'management-review-packager',
      purpose: 'ISO 42001 Clause 9.3.2 management review input package (nine categories).',
      citations: ['ISO/IEC 42001:2023, Clause 9.3.2'] });
  }
  function ArtifactsMgmtReview() {
    var latest = latestFor('management-review-packager');
    if (!latest) return e(EmptyPanel, { message: 'No management review package prepared.' });
    var inputs = latest.inputs || latest.package || {};
    var CATS = [
      { k: 'a', label: 'a. Status of prior actions' },
      { k: 'b', label: 'b. Changes in external/internal issues' },
      { k: 'c', label: 'c. Information on AIMS performance' },
      { k: 'd', label: 'd. Feedback from interested parties' },
      { k: 'e', label: 'e. Results of risk assessment' },
      { k: 'f', label: 'f. Risk treatment status' },
      { k: 'g', label: 'g. Adequacy of resources' },
      { k: 'h', label: 'h. Opportunities for improvement' },
      { k: 'i', label: 'i. Need for changes to the AIMS' },
    ];
    return e('div', { 'data-panel': 'management-review' },
      CATS.map(function(c) {
        var val = inputs[c.k] || inputs[c.label] || inputs['category_' + c.k];
        var hasContent = val && (typeof val === 'string' ? val.length > 0 : (Array.isArray(val) ? val.length > 0 : true));
        return e('details', { key: c.k, className: 'card mb-2', style: { padding: 12 } },
          e('summary', { className: 'font-display font-medium cursor-pointer' }, c.label, ' ',
            e(Badge, { tone: hasContent ? 'ok' : 'warn' }, hasContent ? 'prepared' : 'missing')),
          e('div', { className: 'text-dim text-sm mt-2' },
            typeof val === 'string' ? val : (val ? JSON.stringify(val, null, 2) : 'No input prepared.'))
        );
      })
    );
  }

  function GuidanceAuditPlan() {
    return e(GuidanceSkill, { panelId: 'internal-audit-planner',
      purpose: 'Internal audit schedule plus impartiality assessment for auditor assignments.',
      citations: ['ISO/IEC 42001:2023, Clause 9.2'] });
  }
  function ArtifactsAuditPlan() {
    var latest = latestFor('internal-audit-planner');
    if (!latest) return e(EmptyPanel, { message: 'No internal audit plan prepared.' });
    var schedule = latest.schedule || latest.audits || [];
    var imp = latest.impartiality || latest.impartiality_assessment || {};
    var warns = (imp.warnings || []);
    return e('div', { 'data-panel': 'internal-audit' },
      e('h3', { className: 'font-display text-sm mb-2' }, 'Audit schedule (' + schedule.length + ')'),
      e(SimpleTable, { cols: [
        { key: 'scope', label: 'Scope' },
        { key: 'auditor', label: 'Auditor' },
        { key: 'criteria', label: 'Criteria' },
        { key: 'scheduled_date', label: 'Scheduled', mono: true },
      ], rows: schedule }),
      warns.length > 0
        ? e(Alert, { tone: 'warn' }, 'Impartiality warnings (' + warns.length + '):',
            e('ul', null, warns.map(function(w, i) { return e('li', { key: i }, typeof w === 'string' ? w : JSON.stringify(w)); })))
        : e(Alert, { tone: 'ok' }, 'No impartiality conflicts detected.')
    );
  }

  function GuidanceRoleMatrix() {
    return e(GuidanceSkill, { panelId: 'role-matrix-generator',
      purpose: 'RACI matrix mapping roles to governance decisions.',
      citations: ['ISO/IEC 42001:2023, Clause 5.3'] });
  }
  function ArtifactsRoleMatrix() {
    var latest = latestFor('role-matrix-generator');
    if (!latest) return e(EmptyPanel, { message: 'No role matrix produced.' });
    var rows = latest.matrix || latest.rows || [];
    return e('div', { 'data-panel': 'role-matrix' },
      e('p', { className: 'text-dim text-sm mb-2' }, String(rows.length) + ' role/decision rows.'),
      e(SimpleTable, { cols: [
        { key: 'decision', label: 'Decision' },
        { key: 'role', label: 'Role' },
        { key: 'raci', label: 'RACI', render: function(r) {
          var v = (r.raci || r.assignment || '').toUpperCase();
          var tone = v === 'R' ? 'accent' : v === 'A' ? 'danger' : v === 'C' ? 'info' : v === 'I' ? '' : '';
          return e(Badge, { tone: tone }, v || '-');
        } },
      ], rows: rows, max: 200 })
    );
  }

  function GuidanceNC() {
    return e(GuidanceSkill, { panelId: 'nonconformity-tracker',
      purpose: '8-stage nonconformity lifecycle from detected to closed.',
      citations: ['ISO/IEC 42001:2023, Clause 10.2', 'NIST AI RMF MANAGE 4.2'] });
  }
  function ArtifactsNC() {
    var latest = latestFor('nonconformity');
    if (!latest) return e(EmptyPanel, { message: 'No nonconformity records.' });
    var records = latest.records || [];
    var STAGES = ['detected', 'investigated', 'root-cause-identified', 'corrective-action-planned', 'corrective-action-in-progress', 'effectiveness-reviewed', 'verified', 'closed'];
    var byStage = {};
    STAGES.forEach(function(s) { byStage[s] = []; });
    records.forEach(function(r) { var s = (r && (r.status || r.state)) || 'detected'; if (!byStage[s]) byStage[s] = []; byStage[s].push(r); });
    return e('div', { 'data-panel': 'nonconformity' },
      e('p', { className: 'text-dim text-sm mb-2' }, String(records.length) + ' records across 8 stages.'),
      e('div', { className: 'grid grid-cols-4 gap-2' }, STAGES.map(function(s) {
        return e('div', { key: s, className: 'card', style: { padding: 10 } },
          e('div', { className: 'text-faint text-xs uppercase tracking-wide font-display mb-1' }, s.replace(/-/g, ' ')),
          e('div', { className: 'font-display font-semibold text-md' }, String(byStage[s].length)),
          byStage[s].slice(0, 3).map(function(r, i) {
            return e('div', { key: i, className: 'text-xs text-dim truncate mt-1' }, r.id || r.title || '(no id)');
          })
        );
      }))
    );
  }

  function GuidanceIncident() {
    return e(GuidanceSkill, { panelId: 'incident-reporting',
      purpose: 'Regulatory-deadline-aware external incident reports per jurisdiction.',
      citations: ['EU AI Act, Article 73', 'Colorado SB 205, Section 6-1-1703(7)'] });
  }
  function ArtifactsIncident() {
    var latest = latestFor('incident-reporting');
    if (!latest) return e(EmptyPanel, { message: 'No incident reports drafted.' });
    var deadlines = latest.deadline_matrix || latest.deadlines || [];
    var drafts = latest.reports || latest.drafts || [];
    return e('div', { 'data-panel': 'incident-reporting' },
      e('h3', { className: 'font-display text-sm mb-2' }, 'Deadline matrix'),
      e(SimpleTable, { cols: [
        { key: 'jurisdiction', label: 'Jurisdiction' },
        { key: 'trigger', label: 'Trigger' },
        { key: 'deadline', label: 'Deadline' },
        { key: 'days_remaining', label: 'Days left', render: function(r) {
          var d = r.days_remaining;
          return e(Badge, { tone: d != null && d <= 2 ? 'danger' : d != null && d <= 7 ? 'warn' : 'ok' }, d == null ? '-' : String(d));
        } },
      ], rows: deadlines }),
      e('h3', { className: 'font-display text-sm mt-4 mb-2' }, 'Per-jurisdiction drafts (' + drafts.length + ')'),
      e('div', { className: 'grid grid-cols-2 gap-2' }, drafts.slice(0, 10).map(function(d, i) {
        return e('div', { key: i, className: 'card', style: { padding: 12 } },
          e('div', { className: 'font-display font-medium mb-1' }, d.jurisdiction || d.framework || 'Report ' + (i+1)),
          e('div', { className: 'text-xs text-dim mono' }, (d.status || 'draft')),
          e('div', { className: 'text-sm mt-1 text-dim' }, (d.summary || d.title || '').slice(0, 160))
        );
      }))
    );
  }

  function GuidanceEUConform() {
    return e(GuidanceSkill, { panelId: 'eu-conformity-assessor',
      purpose: 'EU AI Act Article 43 procedure selection, Annex IV completeness, Article 17 QMS.',
      citations: ['EU AI Act, Article 43', 'EU AI Act, Annex IV', 'EU AI Act, Article 17'] });
  }
  function ArtifactsEUConform() {
    var latest = latestFor('eu-conformity-assessor');
    if (!latest) return e(EmptyPanel, { message: 'No EU conformity assessment.' });
    var procedure = latest.procedure || latest.assessment_procedure || '-';
    var annex4 = latest.annex_iv_completeness || latest.annex_iv || [];
    return e('div', { 'data-panel': 'conformity-assessment' },
      e('div', { className: 'card mb-3' },
        e('span', { className: 'text-faint text-xs uppercase tracking-wide font-display' }, 'Procedure'),
        e('div', { className: 'mt-1' }, e(Badge, { tone: 'info' }, String(procedure)))
      ),
      e('h3', { className: 'font-display text-sm mb-2' }, 'Annex IV completeness'),
      e(SimpleTable, { cols: [
        { key: 'element', label: 'Element' },
        { key: 'present', label: 'Present', render: function(r) { return e(Badge, { tone: r.present ? 'ok' : 'danger' }, r.present ? 'yes' : 'no'); } },
        { key: 'evidence_ref', label: 'Evidence', mono: true },
      ], rows: annex4 })
    );
  }

  function GuidanceGPAI() {
    return e(GuidanceSkill, { panelId: 'gpai-obligations-tracker',
      purpose: 'EU AI Act Articles 53, 54, 55 obligations for GPAI providers.',
      citations: ['EU AI Act, Article 51', 'EU AI Act, Article 53', 'EU AI Act, Article 55'] });
  }
  function ArtifactsGPAI() {
    var latest = latestFor('gpai-obligations-tracker');
    if (!latest) return e(EmptyPanel, { message: 'No GPAI obligations record.' });
    var classification = latest.systemic_risk_classification || latest.classification || 'not-systemic';
    var art53 = latest.article_53 || [];
    var art54 = latest.article_54 || [];
    var art55 = latest.article_55 || [];
    function block(label, rows) {
      return e('div', { className: 'card mb-2', style: { padding: 12 } },
        e('div', { className: 'font-display font-medium mb-2' }, label, ' ',
          e(Badge, { tone: '' }, String(rows.length) + ' checks')),
        e(SimpleTable, { cols: [
          { key: 'requirement', label: 'Requirement' },
          { key: 'status', label: 'Status', render: function(r) { return e(Badge, { tone: r.status === 'met' ? 'ok' : r.status === 'gap' ? 'danger' : 'warn' }, r.status || '-'); } },
        ], rows: rows, max: 20 })
      );
    }
    return e('div', { 'data-panel': 'gpai' },
      e('div', { className: 'card mb-3' },
        e('span', { className: 'text-faint text-xs uppercase tracking-wide font-display' }, 'Systemic-risk classification'),
        e('div', { className: 'mt-1' }, e(Badge, { tone: classification === 'systemic-risk' ? 'danger' : 'ok' }, String(classification)))
      ),
      block('Article 53 (universal)', art53),
      block('Article 54 (auth. rep.)', art54),
      block('Article 55 (systemic-risk)', art55)
    );
  }

  function GuidanceOversight() {
    return e(GuidanceSkill, { panelId: 'human-oversight-designer',
      purpose: 'EU AI Act Article 14 oversight design with ability coverage and override capability.',
      citations: ['EU AI Act, Article 14', 'ISO/IEC 42001:2023, Annex A, Control A.9.2', 'NIST AI RMF MANAGE 2.3'] });
  }
  function ArtifactsOversight() {
    var latest = latestFor('human-oversight-designer');
    if (!latest) return e(EmptyPanel, { message: 'No human oversight design recorded.' });
    var abilities = latest.ability_coverage || latest.abilities || [];
    var override = latest.override_capability || latest.override || {};
    var biometric = latest.biometric_dual_assignment;
    return e('div', { 'data-panel': 'human-oversight' },
      e('h3', { className: 'font-display text-sm mb-2' }, '5-ability coverage'),
      e(SimpleTable, { cols: [
        { key: 'ability', label: 'Ability' },
        { key: 'status', label: 'Status', render: function(r) { return e(Badge, { tone: r.status === 'covered' ? 'ok' : r.status === 'partial' ? 'warn' : 'danger' }, r.status || '-'); } },
        { key: 'mechanism', label: 'Mechanism' },
      ], rows: abilities }),
      e('div', { className: 'card mt-3', style: { padding: 12 } },
        e('span', { className: 'text-faint text-xs uppercase tracking-wide font-display' }, 'Override capability'),
        e('div', { className: 'mt-1' }, e(Badge, { tone: override.present ? 'ok' : 'danger' }, override.present ? 'present' : 'missing')),
        override.mechanism ? e('div', { className: 'text-dim text-sm mt-1' }, override.mechanism) : null
      ),
      biometric != null ? e('div', { className: 'card mt-3', style: { padding: 12 } },
        e('span', { className: 'text-faint text-xs uppercase tracking-wide font-display' }, 'Biometric dual-assignment (Article 14(5))'),
        e('div', { className: 'mt-1' }, e(Badge, { tone: biometric === true || biometric === 'compliant' ? 'ok' : 'danger' }, String(biometric)))
      ) : null
    );
  }

  function GuidanceSupplier() {
    return e(GuidanceSkill, { panelId: 'supplier-vendor-assessor',
      purpose: 'Supplier and vendor assessment with independence check.',
      citations: ['ISO/IEC 42001:2023, Annex A, Control A.10.1', 'EU AI Act, Article 25'] });
  }
  function ArtifactsSupplier() {
    var latest = latestFor('supplier-vendor-assessor');
    if (!latest) return e(EmptyPanel, { message: 'No supplier assessments.' });
    var matrix = latest.assessment_matrix || latest.suppliers || [];
    var indep = latest.independence_check || latest.independence || null;
    return e('div', { 'data-panel': 'supplier' },
      e('h3', { className: 'font-display text-sm mb-2' }, 'Assessment matrix (' + matrix.length + ')'),
      e(SimpleTable, { cols: [
        { key: 'supplier', label: 'Supplier' },
        { key: 'role', label: 'Role' },
        { key: 'risk_tier', label: 'Tier', render: function(r) { return e(Badge, { tone: r.risk_tier === 'high' ? 'danger' : r.risk_tier === 'medium' ? 'warn' : 'ok' }, r.risk_tier || '-'); } },
        { key: 'assessment_date', label: 'Assessed', mono: true },
      ], rows: matrix }),
      indep ? e('div', { className: 'card mt-3', style: { padding: 12 } },
        e('span', { className: 'text-faint text-xs uppercase tracking-wide font-display' }, 'Independence check'),
        e('div', { className: 'mt-1' }, e(Badge, { tone: indep.status === 'pass' ? 'ok' : 'danger' }, indep.status || '-')),
        indep.detail ? e('div', { className: 'text-dim text-sm mt-1' }, indep.detail) : null
      ) : null
    );
  }

  function GuidanceUkAtrs() {
    return e(GuidanceSkill, { panelId: 'uk-atrs-recorder',
      purpose: 'UK Algorithmic Transparency Recording Standard (Tier 1 + Tier 2) record.',
      citations: ['UK ATRS v1.0'] });
  }
  function ArtifactsUkAtrs() {
    var latest = latestFor('uk-atrs');
    if (!latest) return e(EmptyPanel, { message: 'No UK ATRS records.' });
    var t1 = latest.tier_1 || latest.tier1 || {};
    var t2 = latest.tier_2 || latest.tier2 || {};
    function section(label, obj) {
      var entries = Object.keys(obj || {}).slice(0, 20);
      return e('details', { className: 'card mb-2', style: { padding: 12 } },
        e('summary', { className: 'font-display font-medium cursor-pointer' }, label, ' ',
          e(Badge, { tone: entries.length > 0 ? 'ok' : 'warn' }, entries.length + ' fields')),
        e('dl', { className: 'mt-2 text-sm' }, entries.map(function(k) {
          var val = obj[k];
          return e('div', { key: k, className: 'mb-1' },
            e('dt', { className: 'text-faint text-xs uppercase tracking-wide font-display' }, k.replace(/_/g, ' ')),
            e('dd', { className: 'text-dim' }, typeof val === 'string' ? val : JSON.stringify(val)));
        }))
      );
    }
    return e('div', { 'data-panel': 'uk-atrs' },
      section('Tier 1 summary', t1),
      section('Tier 2 sections', t2)
    );
  }

  function GuidanceColorado() {
    return e(GuidanceSkill, { panelId: 'colorado-ai-act-compliance',
      purpose: 'Colorado SB 205 developer and deployer obligation matrix.',
      citations: ['Colorado SB 205, Section 6-1-1702', 'Colorado SB 205, Section 6-1-1703'] });
  }
  function ArtifactsColorado() {
    var latest = latestFor('colorado-ai-act');
    if (!latest) return e(EmptyPanel, { message: 'No Colorado SB 205 compliance records.' });
    var dev = latest.developer_obligations || [];
    var dep = latest.deployer_obligations || [];
    var safe = latest.safe_harbor || latest.safe_harbour || {};
    function mx(label, rows) {
      return e('div', { className: 'card mb-2', style: { padding: 12 } },
        e('div', { className: 'font-display font-medium mb-2' }, label),
        e(SimpleTable, { cols: [
          { key: 'obligation', label: 'Obligation' },
          { key: 'status', label: 'Status', render: function(r) { return e(Badge, { tone: r.status === 'met' ? 'ok' : 'danger' }, r.status || '-'); } },
          { key: 'section', label: 'Section', mono: true },
        ], rows: rows })
      );
    }
    return e('div', { 'data-panel': 'colorado-ai-act' },
      mx('Developer obligations', dev),
      mx('Deployer obligations', dep),
      e('div', { className: 'card', style: { padding: 12 } },
        e('span', { className: 'text-faint text-xs uppercase tracking-wide font-display' }, 'Safe-harbor status'),
        e('div', { className: 'mt-1' }, e(Badge, { tone: safe.eligible ? 'ok' : 'warn' }, safe.eligible ? 'eligible' : 'not eligible'))
      )
    );
  }

  function GuidanceNycLl144() {
    return e(GuidanceSkill, { panelId: 'nyc-ll144-audit-packager',
      purpose: 'NYC Local Law 144 bias audit public-disclosure bundle with impact ratios and 4/5ths visualization.',
      citations: ['NYC LL144, Section 20-871', 'NYC LL144, Section 5-303'] });
  }
  function ArtifactsNycLl144() {
    var latest = latestFor('nyc-ll144');
    if (!latest) return e(EmptyPanel, { message: 'No NYC LL 144 audit packages.' });
    var ratios = latest.impact_ratios || latest.ratios || [];
    var notice = latest.candidate_notice || {};
    return e('div', { 'data-panel': 'nyc-ll144' },
      e('h3', { className: 'font-display text-sm mb-2' }, 'Impact ratio table'),
      e(SimpleTable, { cols: [
        { key: 'group', label: 'Group' },
        { key: 'selection_rate', label: 'Selection rate', mono: true },
        { key: 'impact_ratio', label: 'Impact ratio', mono: true },
        { key: 'four_fifths', label: '4/5ths', render: function(r) {
          var passes = (typeof r.impact_ratio === 'number' && r.impact_ratio >= 0.8) || r.four_fifths === 'pass';
          return e(Badge, { tone: passes ? 'ok' : 'danger' }, passes ? 'pass' : 'fail');
        } },
      ], rows: ratios }),
      e('div', { className: 'card mt-3', style: { padding: 12 } },
        e('span', { className: 'text-faint text-xs uppercase tracking-wide font-display' }, 'Candidate notice'),
        e('div', { className: 'mt-1' }, e(Badge, { tone: notice.posted ? 'ok' : 'danger' }, notice.posted ? 'posted' : 'not posted')),
        notice.url ? e('div', { className: 'mono text-xs mt-1' }, String(notice.url)) : null
      )
    );
  }

  function GuidanceMagf() {
    return e(GuidanceSkill, { panelId: 'singapore-magf-assessor',
      purpose: 'Singapore MAGF 4-pillar assessment with MAS FEAT financial-services layering.',
      citations: ['Singapore MAGF v2e', 'MAS FEAT Principles'] });
  }
  function ArtifactsMagf() {
    var latest = latestFor('singapore-magf-assessor');
    if (!latest) return e(EmptyPanel, { message: 'No MAGF assessments.' });
    var pillars = latest.pillars || [];
    var feat = latest.feat || latest.mas_feat;
    return e('div', { 'data-panel': 'singapore-magf' },
      e('div', { className: 'grid grid-cols-4 gap-2 mb-3' }, pillars.slice(0, 4).map(function(p, i) {
        return e('div', { key: i, className: 'tile' },
          e('span', { className: 'count ' + (p.score === 'mature' ? 'ok' : p.score === 'developing' ? 'warn' : 'danger') }, String(p.score || '-')),
          e('span', { className: 'label' }, p.name || ('Pillar ' + (i+1)))
        );
      })),
      feat ? e('div', { className: 'card', style: { padding: 12 } },
        e('span', { className: 'text-faint text-xs uppercase tracking-wide font-display' }, 'MAS FEAT (financial services)'),
        e(SimpleTable, { cols: [
          { key: 'principle', label: 'Principle' },
          { key: 'status', label: 'Status', render: function(r) { return e(Badge, { tone: r.status === 'met' ? 'ok' : 'danger' }, r.status || '-'); } },
        ], rows: Array.isArray(feat) ? feat : (feat.principles || []) })
      ) : null
    );
  }

  function GuidanceExplain() {
    return e(GuidanceSkill, { panelId: 'explainability-documenter',
      purpose: 'Explainability methods coverage matrix and EU AI Act Article 86 readiness.',
      citations: ['NIST AI RMF MEASURE 2.9', 'EU AI Act, Article 86', 'ISO/IEC 42001:2023, Annex A, Control A.8.2'] });
  }
  function ArtifactsExplain() {
    var latest = latestFor('explainability-documenter');
    if (!latest) return e(EmptyPanel, { message: 'No explainability docs.' });
    var coverage = latest.methods_coverage || latest.coverage || [];
    var art86 = latest.article_86_readiness || latest.art86 || null;
    return e('div', { 'data-panel': 'explainability' },
      e('h3', { className: 'font-display text-sm mb-2' }, 'Methods coverage matrix'),
      e(SimpleTable, { cols: [
        { key: 'scope', label: 'Scope' },
        { key: 'method', label: 'Method' },
        { key: 'audience', label: 'Audience' },
        { key: 'status', label: 'Status', render: function(r) { return e(Badge, { tone: r.status === 'present' ? 'ok' : 'danger' }, r.status || '-'); } },
      ], rows: coverage }),
      art86 != null ? e('div', { className: 'card mt-3', style: { padding: 12 } },
        e('span', { className: 'text-faint text-xs uppercase tracking-wide font-display' }, 'EU AI Act Article 86 readiness'),
        e('div', { className: 'mt-1' }, e(Badge, { tone: art86 === 'ready' || art86 === true ? 'ok' : 'warn' }, String(art86)))
      ) : null
    );
  }

  function GuidanceEventLog() {
    return e(GuidanceSkill, { panelId: 'system-event-logger',
      purpose: 'Event schema, retention policy, tamper-evidence per EU AI Act Article 12/19.',
      citations: ['EU AI Act, Article 12', 'EU AI Act, Article 19', 'ISO/IEC 42001:2023, Annex A, Control A.6.2.8'] });
  }
  function ArtifactsEventLog() {
    var latest = latestFor('system-event-logger');
    if (!latest) return e(EmptyPanel, { message: 'No system event log schema recorded.' });
    var schema = latest.event_schema || latest.schema || [];
    var retention = latest.retention_policy || latest.retention || {};
    var tamper = latest.tamper_evidence || latest.tamper || null;
    return e('div', { 'data-panel': 'system-event-log' },
      e('h3', { className: 'font-display text-sm mb-2' }, 'Event schema'),
      e(SimpleTable, { cols: [
        { key: 'field', label: 'Field', mono: true },
        { key: 'type', label: 'Type' },
        { key: 'required', label: 'Required', render: function(r) { return e(Badge, { tone: r.required ? 'accent' : '' }, r.required ? 'yes' : 'no'); } },
        { key: 'description', label: 'Description' },
      ], rows: schema }),
      e('div', { className: 'card mt-3', style: { padding: 12 } },
        e('span', { className: 'text-faint text-xs uppercase tracking-wide font-display' }, 'Retention policy'),
        e('div', { className: 'mt-1 text-dim text-sm' },
          'Minimum: ' + String(retention.minimum_months || retention.min || '-') + ' months'),
        retention.maximum_months ? e('div', { className: 'text-dim text-sm' }, 'Maximum: ' + retention.maximum_months + ' months') : null
      ),
      tamper != null ? e('div', { className: 'card mt-2', style: { padding: 12 } },
        e('span', { className: 'text-faint text-xs uppercase tracking-wide font-display' }, 'Tamper evidence'),
        e('div', { className: 'mt-1' }, e(Badge, { tone: tamper === true || tamper === 'enabled' ? 'ok' : 'warn' }, String(tamper)))
      ) : null
    );
  }

  function GuidanceGenai() {
    return e(GuidanceSkill, { panelId: 'genai-risk-register',
      purpose: 'NIST AI 600-1 GenAI Profile 12-risk register with inherent and residual scoring.',
      citations: ['NIST AI 600-1 (July 2024)', 'EU AI Act, Article 50', 'EU AI Act, Article 55'] });
  }
  function ArtifactsGenai() {
    var latest = latestFor('genai-risk-register');
    if (!latest) return e(EmptyPanel, { message: 'No GenAI risk register recorded.' });
    var risks = latest.risks || latest.rows || [];
    return e('div', { 'data-panel': 'genai-risk' },
      e('p', { className: 'text-dim text-sm mb-2' }, String(risks.length) + ' of 12 GenAI risks evaluated.'),
      e(SimpleTable, { cols: [
        { key: 'risk_id', label: 'ID', mono: true },
        { key: 'name', label: 'Risk' },
        { key: 'inherent_score', label: 'Inherent', mono: true },
        { key: 'residual_score', label: 'Residual', mono: true },
        { key: 'escalated', label: 'Escalation', render: function(r) { return e(Badge, { tone: r.escalated ? 'danger' : 'ok' }, r.escalated ? 'flagged' : 'ok'); } },
      ], rows: risks, max: 20 })
    );
  }

  function GuidanceDataReg() {
    return e(GuidanceSkill, { panelId: 'data-register-builder',
      purpose: 'Data register per ISO 42001 A.7 and EU AI Act Article 10 (datasets, provenance, retention).',
      citations: ['ISO/IEC 42001:2023, Annex A, Control A.7.1', 'EU AI Act, Article 10'] });
  }
  function ArtifactsDataReg() {
    var latest = latestFor('data-register-builder');
    if (!latest) return e(EmptyPanel, { message: 'No data register entries.' });
    var datasets = latest.datasets || latest.rows || [];
    return e('div', { 'data-panel': 'data-register' },
      e('p', { className: 'text-dim text-sm mb-2' }, String(datasets.length) + ' datasets registered.'),
      e(SimpleTable, { cols: [
        { key: 'dataset_id', label: 'ID', mono: true },
        { key: 'name', label: 'Name' },
        { key: 'provenance', label: 'Provenance' },
        { key: 'retention', label: 'Retention', mono: true },
        { key: 'lawful_basis', label: 'Lawful basis' },
      ], rows: datasets })
    );
  }

  function GuidanceCrosswalkMatrix() {
    return e(GuidanceSkill, { panelId: 'crosswalk-matrix-builder',
      purpose: 'Cross-framework coverage matrix and query results.',
      citations: ['See crosswalk browser for full graph'] });
  }
  function ArtifactsCrosswalkMatrix() {
    var latest = latestFor('crosswalk-matrix-builder');
    var cw = DATA.crosswalk || { mappings: [] };
    if (!latest && (cw.mappings || []).length === 0) return e(EmptyPanel, { message: 'No crosswalk matrix queries recorded.' });
    var query = latest && (latest.query || latest.parameters) || {};
    var results = (latest && (latest.results || latest.rows)) || cw.mappings.slice(0, 40);
    return e('div', { 'data-panel': 'crosswalk-matrix' },
      Object.keys(query).length > 0 ? e('div', { className: 'card mb-3', style: { padding: 12 } },
        e('span', { className: 'text-faint text-xs uppercase tracking-wide font-display' }, 'Query'),
        e('pre', { className: 'mono text-xs mt-1' }, JSON.stringify(query, null, 2))
      ) : null,
      e(SimpleTable, { cols: [
        { key: 'source_fw', label: 'Source' },
        { key: 'source_ref', label: 'Source ref', mono: true },
        { key: 'target_fw', label: 'Target' },
        { key: 'target_ref', label: 'Target ref', mono: true },
        { key: 'relationship', label: 'Relationship' },
      ], rows: results, max: 100 })
    );
  }

  function GuidanceHighRisk() {
    return e(GuidanceSkill, { panelId: 'high-risk-classifier',
      purpose: 'EU AI Act risk-tier classification per Articles 5, 6 and Annex I/III.',
      citations: ['EU AI Act, Article 5', 'EU AI Act, Article 6', 'EU AI Act, Annex I', 'EU AI Act, Annex III'] });
  }
  function ArtifactsHighRisk() {
    var latest = latestFor('classification');
    if (!latest) return e(EmptyPanel, { message: 'No classification artifacts.' });
    var systems = latest.systems || latest.rows || [latest];
    return e('div', { 'data-panel': 'high-risk-classifier' },
      e(SimpleTable, { cols: [
        { key: 'system_id', label: 'System', mono: true },
        { key: 'tier', label: 'Tier', render: function(r) { var t = r.tier || r.risk_tier; return e(Badge, { tone: t === 'prohibited' ? 'danger' : t === 'high' ? 'danger' : t === 'limited' ? 'warn' : 'ok' }, t || '-'); } },
        { key: 'annex', label: 'Annex', render: function(r) { return r.annex ? e(Badge, { tone: 'info' }, r.annex) : '-'; } },
        { key: 'justification', label: 'Justification' },
      ], rows: systems })
    );
  }

  // ------------------------------------------------------------------
  // Panel factory map. Each entry is a triple of React components.
  // ------------------------------------------------------------------

  var PANEL_FACTORIES = {
    'framework-monitor':             { Guidance: GuidanceRegFeed,       Artifacts: ArtifactsRegFeed,       storeKey: 'framework-monitor' },
    'applicability-checker':         { Guidance: GuidanceApplicability, Artifacts: ArtifactsApplicability, storeKey: 'applicability-checker' },
    'gap-explorer':                  { Guidance: GuidanceGapExplorer,   Artifacts: ArtifactsGapExplorer,   storeKey: 'gap-assessment' },
    'citation-search':               { Guidance: GuidanceCitationSearch,Artifacts: ArtifactsCitationSearch,storeKey: null },
    'ai-system-inventory-maintainer':{ Guidance: GuidanceAISystems,     Artifacts: ArtifactsAISystems,     storeKey: 'ai-system-inventory-maintainer' },
    'aisia-runner':                  { Guidance: GuidanceAISIA,         Artifacts: ArtifactsAISIA,         storeKey: 'aisia' },
    'audit-log-generator':           { Guidance: GuidanceAuditLog,      Artifacts: ArtifactsAuditLog,      storeKey: 'audit-log-generator' },
    'metrics-collector':             { Guidance: GuidanceMetrics,       Artifacts: ArtifactsMetrics,       storeKey: 'metrics' },
    'post-market-monitoring':        { Guidance: GuidancePMM,           Artifacts: ArtifactsPMM,           storeKey: 'post-market-monitoring' },
    'robustness-evaluator':          { Guidance: GuidanceRobustness,    Artifacts: ArtifactsRobustness,    storeKey: 'robustness-evaluator' },
    'bias-evaluator':                { Guidance: GuidanceBias,          Artifacts: ArtifactsBias,          storeKey: 'bias-evaluator' },
    'evidence-bundle-packager':      { Guidance: GuidanceBundle,        Artifacts: ArtifactsBundle,        storeKey: 'evidence-bundle-packager' },
    'certification-readiness':       { Guidance: GuidanceCertReady,     Artifacts: ArtifactsCertReady,     storeKey: 'certification-readiness' },
    'management-review-packager':    { Guidance: GuidanceMgmtReview,    Artifacts: ArtifactsMgmtReview,    storeKey: 'management-review-packager' },
    'internal-audit-planner':        { Guidance: GuidanceAuditPlan,     Artifacts: ArtifactsAuditPlan,     storeKey: 'internal-audit-planner' },
    'role-matrix-generator':         { Guidance: GuidanceRoleMatrix,    Artifacts: ArtifactsRoleMatrix,    storeKey: 'role-matrix-generator' },
    'nonconformity-tracker':         { Guidance: GuidanceNC,            Artifacts: ArtifactsNC,            storeKey: 'nonconformity' },
    'incident-reporting':            { Guidance: GuidanceIncident,      Artifacts: ArtifactsIncident,      storeKey: 'incident-reporting' },
    'eu-conformity-assessor':        { Guidance: GuidanceEUConform,     Artifacts: ArtifactsEUConform,     storeKey: 'eu-conformity-assessor' },
    'gpai-obligations-tracker':      { Guidance: GuidanceGPAI,          Artifacts: ArtifactsGPAI,          storeKey: 'gpai-obligations-tracker' },
    'human-oversight-designer':      { Guidance: GuidanceOversight,     Artifacts: ArtifactsOversight,     storeKey: 'human-oversight-designer' },
    'supplier-vendor-assessor':      { Guidance: GuidanceSupplier,      Artifacts: ArtifactsSupplier,      storeKey: 'supplier-vendor-assessor' },
    'uk-atrs-recorder':              { Guidance: GuidanceUkAtrs,        Artifacts: ArtifactsUkAtrs,        storeKey: 'uk-atrs' },
    'colorado-ai-act-compliance':    { Guidance: GuidanceColorado,      Artifacts: ArtifactsColorado,      storeKey: 'colorado-ai-act' },
    'nyc-ll144-audit-packager':      { Guidance: GuidanceNycLl144,      Artifacts: ArtifactsNycLl144,      storeKey: 'nyc-ll144' },
    'singapore-magf-assessor':       { Guidance: GuidanceMagf,          Artifacts: ArtifactsMagf,          storeKey: 'singapore-magf-assessor' },
    'explainability-documenter':     { Guidance: GuidanceExplain,       Artifacts: ArtifactsExplain,       storeKey: 'explainability-documenter' },
    'system-event-logger':           { Guidance: GuidanceEventLog,      Artifacts: ArtifactsEventLog,      storeKey: 'system-event-logger' },
    'genai-risk-register':           { Guidance: GuidanceGenai,         Artifacts: ArtifactsGenai,         storeKey: 'genai-risk-register' },
    'data-register-builder':         { Guidance: GuidanceDataReg,       Artifacts: ArtifactsDataReg,       storeKey: 'data-register-builder' },
    'crosswalk-matrix-builder':      { Guidance: GuidanceCrosswalkMatrix,Artifacts: ArtifactsCrosswalkMatrix, storeKey: 'crosswalk-matrix-builder' },
    'high-risk-classifier':          { Guidance: GuidanceHighRisk,      Artifacts: ArtifactsHighRisk,      storeKey: 'classification' },
  };

  function EvidenceQuickAction(props) {
    return e('div', { className: 'mt-4' },
      e(Button, {
        title: 'Open evidence bundle inspector with this panel pre-selected',
        onClick: function() { window.location.hash = '#/evidence-bundle-packager'; },
      }, 'Inspect evidence bundle')
    );
  }

  // Panel dispatch. Each returns the full PanelHeader + card + workspace.
  // props.server is the shared server state object (health + tasks + approvals
  // + commands) used by the Command Center components. Non-Command-Center
  // panels ignore it.
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

    if (id === 'command-center') {
      return e(CommandCenterPanel, { server: props.server });
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

    // Bespoke renderer triples for every non-specially-handled panel.
    var factory = PANEL_FACTORIES[id];
    if (factory) {
      return e('div', null,
        e(PanelHeader, { crumbs: crumbs, title: title, desc: desc }),
        e(Card, { panelId: id },
          e(ThreeTabWorkspace, {
            guidance:   e(factory.Guidance, null),
            artifacts:  e('div', null, e(factory.Artifacts, null), e(EvidenceQuickAction, null)),
            validation: factory.storeKey
              ? e(ValidationFromWarnings, { storeKey: factory.storeKey })
              : e(Alert, { tone: 'ok' }, 'Client-side panel. No server-side warnings apply.'),
          })
        )
      );
    }

    // True fallback: only reached for unknown panel ids. Surfaces the issue
    // so new panels added to the catalogue but missing from PANEL_FACTORIES
    // are visible rather than silently rendering a placeholder.
    return e('div', null,
      e(PanelHeader, { crumbs: crumbs, title: title, desc: desc }),
      e(Card, { panelId: id },
        e(Alert, { tone: 'warn' }, 'Unregistered panel id: ' + id + '. Add a factory entry in PANEL_FACTORIES.'),
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

    var _exec = useState(!!safeGet(EXEC_VIEW_KEY, false));
    var execView = _exec[0]; var setExecView = _exec[1];

    // Server state: health, tasks, approvals, commands. Polled.
    var server = useServerState();

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

    function toggleExec() {
      var next = !execView;
      setExecView(next);
      safeSet(EXEC_VIEW_KEY, next);
    }

    if (!DATA.has_any_artifacts && route === 'dashboard') {
      // Welcome page replaces dashboard when the store is empty.
      return e('div', { className: 'app-shell' },
        e(Sidebar, { collapsed: collapsed, setCollapsed: setCollapsed, route: route, navigate: navigate }),
        e('div', { className: 'main-col' },
          e(ActionBanner, { data: DATA.action_required }),
          e(HealthStrip, { server: server }),
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
          e(Button, {
            onClick: toggleExec,
            title: 'Switch between executive and operating views',
          }, execView ? 'Operating view' : 'Executive view'),
          e(Button, { onClick: function() { setCmdOpen(true); }, title: 'Search (press /)' }, 'Search ', e('kbd', null, '/'))
        ),
        e(HealthStrip, { server: server }),
        e('main', { id: 'content', className: 'content anim-fade-in-up' },
          execView ? e(ExecutiveView, { server: server }) : e(Panel, { id: route, server: server })
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
