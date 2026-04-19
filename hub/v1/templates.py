"""HTML template fragments for AIGovClaw Hub v1.

v1 is the React + Tailwind-subset + shadcn-shaped artifact variant. It is a
single self-contained HTML file with:

  - React 18 UMD bundle inlined from hub/v1/vendor/react.production.min.js
    and hub/v1/vendor/react-dom.production.min.js.
  - A hand-curated subset of Tailwind-like utility classes inlined as CSS.
  - shadcn/ui shapes (Card, Table, Tabs, Badge, Button, Alert) re-implemented
    as plain React functional components using the curated utilities.
  - Application state rendered from a JSON payload inlined into the page.

No build step. No npm. No CDN. No network at runtime.

Aesthetic bar matches v0 exactly: JetBrains Mono display, Crimson Pro body,
burnt-orange accent #d97757 on deep slate #0f1419.
"""

from __future__ import annotations


# --------------------------------------------------------------------------
# CSS: Tailwind-like curated utilities + v0 aesthetic tokens
# --------------------------------------------------------------------------

# Hand-written, covers only the classes the v1 React components use. ~20 KB.
# All colors expressed as CSS variables from the v0 palette so v1 cannot
# drift from the brand bar.
TAILWIND_SUBSET_CSS = """
:root {
  --bg: #0f1419;
  --surface: #1a1f26;
  --surface-2: #222833;
  --surface-3: #2a313d;
  --accent: #d97757;
  --accent-dim: #8a4a37;
  --text: #e5e7eb;
  --text-dim: #9ca3af;
  --text-faint: #6b7280;
  --border: #2a2f38;
  --border-strong: #3a414e;
  --ok: #4ade80;
  --warn: #f59e0b;
  --danger: #ef4444;
  --radius: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --font-display: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --font-body: 'Crimson Pro', Georgia, 'Iowan Old Style', serif;
}

* { box-sizing: border-box; }

html, body {
  margin: 0; padding: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
  font-size: 17px;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}

body::before {
  content: "";
  position: fixed; inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 15% 10%, rgba(217,119,87,0.06), transparent 40%),
    radial-gradient(circle at 85% 85%, rgba(217,119,87,0.04), transparent 45%);
  z-index: 0;
}

#root { position: relative; z-index: 1; }

/* Typography reset inside the app */
h1, h2, h3, h4, p, ul, ol { margin: 0; }
button { font: inherit; cursor: pointer; }
input { font: inherit; }

/* Layout primitives */
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

.items-start { align-items: flex-start; }
.items-center { align-items: center; }
.items-end { align-items: flex-end; }
.items-baseline { align-items: baseline; }
.justify-start { justify-content: flex-start; }
.justify-center { justify-content: center; }
.justify-between { justify-content: space-between; }
.justify-end { justify-content: flex-end; }

.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.gap-4 { gap: 16px; }
.gap-6 { gap: 24px; }
.gap-8 { gap: 32px; }

.grid-cols-1 { grid-template-columns: 1fr; }
.grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.grid-cols-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.grid-cols-auto-fit { grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); }

/* Spacing */
.m-0 { margin: 0; }
.mx-auto { margin-left: auto; margin-right: auto; }
.mt-1 { margin-top: 4px; }
.mt-2 { margin-top: 8px; }
.mt-3 { margin-top: 12px; }
.mt-4 { margin-top: 16px; }
.mt-6 { margin-top: 24px; }
.mt-8 { margin-top: 32px; }
.mb-2 { margin-bottom: 8px; }
.mb-3 { margin-bottom: 12px; }
.mb-4 { margin-bottom: 16px; }
.mb-6 { margin-bottom: 24px; }
.mb-8 { margin-bottom: 32px; }
.mr-2 { margin-right: 8px; }

.p-1 { padding: 4px; }
.p-2 { padding: 8px; }
.p-3 { padding: 12px; }
.p-4 { padding: 16px; }
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
.pt-4 { padding-top: 16px; }
.pb-4 { padding-bottom: 16px; }

.max-w-screen { max-width: 1280px; }
.w-full { width: 100%; }
.w-auto { width: auto; }
.min-w-0 { min-width: 0; }

/* Sizing */
.h-full { height: 100%; }
.h-2 { height: 8px; }
.h-6 { height: 24px; }

/* Borders and radius */
.border { border: 1px solid var(--border); }
.border-t { border-top: 1px solid var(--border); }
.border-b { border-bottom: 1px solid var(--border); }
.border-l { border-left: 1px solid var(--border); }
.border-strong { border-color: var(--border-strong); }
.border-accent { border-color: var(--accent); }
.rounded { border-radius: var(--radius); }
.rounded-md { border-radius: var(--radius-md); }
.rounded-lg { border-radius: var(--radius-lg); }
.rounded-full { border-radius: 9999px; }

/* Backgrounds */
.bg-bg { background: var(--bg); }
.bg-surface { background: var(--surface); }
.bg-surface-2 { background: var(--surface-2); }
.bg-surface-3 { background: var(--surface-3); }
.bg-accent { background: var(--accent); }
.bg-transparent { background: transparent; }

/* Text */
.text-text { color: var(--text); }
.text-dim { color: var(--text-dim); }
.text-faint { color: var(--text-faint); }
.text-accent { color: var(--accent); }
.text-ok { color: var(--ok); }
.text-warn { color: var(--warn); }
.text-danger { color: var(--danger); }
.text-bg { color: var(--bg); }

.text-xs { font-size: 11px; }
.text-sm { font-size: 13px; }
.text-base { font-size: 15px; }
.text-md { font-size: 17px; }
.text-lg { font-size: 20px; }
.text-xl { font-size: 24px; }
.text-2xl { font-size: 32px; }
.text-3xl { font-size: 42px; }

.font-display { font-family: var(--font-display); }
.font-body { font-family: var(--font-body); }
.font-normal { font-weight: 400; }
.font-medium { font-weight: 500; }
.font-semibold { font-weight: 600; }

.uppercase { text-transform: uppercase; }
.tracking-wide { letter-spacing: 0.14em; }
.tracking-wider { letter-spacing: 0.18em; }
.text-left { text-align: left; }
.text-right { text-align: right; }
.text-center { text-align: center; }
.break-all { word-break: break-all; }
.leading-tight { line-height: 1.1; }
.leading-normal { line-height: 1.55; }

/* Pointer and selection */
.cursor-pointer { cursor: pointer; }
.select-none { user-select: none; }
.outline-none { outline: none; }

/* Positioning */
.relative { position: relative; }
.absolute { position: absolute; }
.sticky { position: sticky; }
.top-0 { top: 0; }
.z-10 { z-index: 10; }
.z-20 { z-index: 20; }

/* Overflow */
.overflow-x-auto { overflow-x: auto; }
.overflow-hidden { overflow: hidden; }

/* Transitions */
.transition { transition: all 160ms ease; }
.transition-colors { transition: color 160ms ease, background-color 160ms ease, border-color 160ms ease; }

/* Hover */
.hover-accent:hover { color: var(--accent); }
.hover-border-accent:hover { border-color: var(--accent); }
.hover-bg-surface-2:hover { background: var(--surface-2); }

/* Focus ring */
.focus-ring:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

/* Links */
a {
  color: var(--accent);
  text-decoration: none;
  border-bottom: 1px dotted var(--accent-dim);
}
a:hover { color: var(--text); border-bottom-color: var(--text); }

/* Table */
table { width: 100%; border-collapse: collapse; }
th, td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}
th {
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-dim);
  background: var(--surface-2);
  cursor: pointer;
  user-select: none;
}
th:hover { color: var(--accent); }
td { font-family: var(--font-body); font-size: 15px; }
td.mono, .mono { font-family: var(--font-display); font-size: 13px; }

/* Filter input */
.filter-input {
  width: 100%;
  padding: 6px 8px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-family: var(--font-display);
  font-size: 12px;
}
.filter-input:focus { outline: 2px solid var(--accent); outline-offset: -1px; border-color: var(--accent); }

/* Coverage bar */
.bar-track {
  flex: 1;
  height: 6px;
  background: var(--surface-2);
  border-radius: 3px;
  overflow: hidden;
}
.bar-fill { height: 100%; background: var(--accent); }

/* Accessibility */
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}

@media (prefers-contrast: more) {
  :root { --border: #4a4f58; --text-dim: #cbd5e1; }
}

.skip-link {
  position: absolute; left: -9999px; top: 0;
}
.skip-link:focus {
  left: 16px; top: 16px;
  background: var(--accent); color: var(--bg);
  padding: 8px 12px; border-radius: var(--radius); z-index: 100;
}

/* Responsive */
@media (max-width: 900px) {
  .grid-cols-2, .grid-cols-3, .grid-cols-4 { grid-template-columns: 1fr; }
}
"""


# --------------------------------------------------------------------------
# React application code
# --------------------------------------------------------------------------

# Plain React via React.createElement. No JSX, no transpilation needed.
# shadcn-shaped components implemented as small functional components.
APP_JS = r"""
(function() {
  'use strict';
  var e = React.createElement;
  var useState = React.useState;
  var useEffect = React.useEffect;
  var useMemo = React.useMemo;
  var useRef = React.useRef;

  var DATA = window.__AIGOVCLAW_HUB_DATA__ || {};

  // ------------------------------------------------------------------
  // shadcn-shaped primitives
  // ------------------------------------------------------------------

  function cx() {
    var out = [];
    for (var i = 0; i < arguments.length; i++) {
      var v = arguments[i];
      if (typeof v === 'string' && v) out.push(v);
    }
    return out.join(' ');
  }

  function Card(props) {
    return e('section', {
      className: cx('bg-surface border rounded p-6 mb-6', props.className),
      'data-jurisdiction': props.jurisdiction || 'global',
      role: 'region',
      'aria-labelledby': props.titleId,
    }, props.children);
  }

  function CardHeader(props) {
    return e('header', {
      className: 'flex items-baseline justify-between mb-4 pb-3 border-b',
    }, props.children);
  }

  function CardTitle(props) {
    return e('h2', {
      id: props.id,
      className: 'font-display font-medium text-lg flex items-baseline gap-3',
    },
      e('span', { className: 'text-accent text-xs tracking-wide' }, props.num),
      e('span', null, props.children)
    );
  }

  function CardContent(props) {
    return e('div', { className: cx('mt-2', props.className) }, props.children);
  }

  function Badge(props) {
    var tone = props.tone || 'default';
    var toneCls = {
      ok: 'text-ok',
      warn: 'text-warn',
      danger: 'text-danger',
      accent: 'text-accent',
      default: 'text-dim',
    }[tone] || 'text-dim';
    var toneBorder = {
      ok: 'border-ok',
      warn: 'border-warn',
      danger: 'border-danger',
      accent: 'border-accent',
      default: '',
    }[tone] || '';
    return e('span', {
      className: cx(
        'inline-block font-display text-xs uppercase tracking-wide',
        'px-2 py-1 rounded-full border',
        toneCls, toneBorder
      ),
      style: toneBorder ? { borderColor: 'var(--' + tone + ')' } : null,
    }, props.children);
  }

  function Button(props) {
    return e('button', {
      type: 'button',
      onClick: props.onClick,
      className: cx(
        'font-display text-xs uppercase tracking-wide',
        'px-3 py-1 rounded border bg-transparent text-dim',
        'hover-border-accent hover-accent transition-colors focus-ring',
        props.className
      ),
      title: props.title,
    }, props.children);
  }

  function Alert(props) {
    var tone = props.tone || 'warn';
    return e('div', {
      className: cx('border rounded p-4 mb-4 font-display text-sm'),
      style: { borderColor: 'var(--' + tone + ')', color: 'var(--' + tone + ')' },
      role: 'alert',
    }, props.children);
  }

  // Tabs (shadcn-shaped): tablist + tab + tabpanel wiring.
  function Tabs(props) {
    var items = props.items;
    var value = props.value;
    var onChange = props.onChange;
    var refs = useRef([]);

    function onKeyDown(idx) {
      return function(ev) {
        if (ev.key === 'ArrowRight' || ev.key === 'ArrowLeft') {
          ev.preventDefault();
          var dir = ev.key === 'ArrowRight' ? 1 : -1;
          var next = (idx + dir + items.length) % items.length;
          var el = refs.current[next];
          if (el) { el.focus(); onChange(items[next].value); }
        } else if (ev.key === 'Home') {
          ev.preventDefault();
          refs.current[0] && refs.current[0].focus();
          onChange(items[0].value);
        } else if (ev.key === 'End') {
          ev.preventDefault();
          var last = items.length - 1;
          refs.current[last] && refs.current[last].focus();
          onChange(items[last].value);
        }
      };
    }

    return e('nav', {
      className: 'sticky top-0 z-20 bg-bg border-b mb-6 py-3',
      'aria-label': 'Jurisdiction filter',
    },
      e('ul', {
        role: 'tablist',
        className: 'flex gap-2 m-0 p-0',
        style: { listStyle: 'none' },
      }, items.map(function(it, idx) {
        var selected = it.value === value;
        return e('li', { key: it.value },
          e('button', {
            ref: function(el) { refs.current[idx] = el; },
            type: 'button',
            role: 'tab',
            id: 'tab-' + it.value,
            'aria-selected': selected ? 'true' : 'false',
            tabIndex: selected ? 0 : -1,
            onClick: function() { onChange(it.value); },
            onKeyDown: onKeyDown(idx),
            className: cx(
              'font-display text-xs uppercase tracking-wide',
              'px-4 py-2 rounded border bg-surface',
              'transition-colors focus-ring',
              selected ? 'text-accent border-accent' : 'text-faint hover-accent hover-border-accent'
            ),
          }, it.label)
        );
      }))
    );
  }

  // Sortable, filterable Table.
  function DataTable(props) {
    var columns = props.columns;
    var rows = props.rows;
    var initialSort = props.initialSort || null;
    var storageKey = props.storageKey;

    var _sort = useState(initialSort);
    var sort = _sort[0]; var setSort = _sort[1];
    var _filters = useState({});
    var filters = _filters[0]; var setFilters = _filters[1];

    function clickHeader(key) {
      setSort(function(prev) {
        if (prev && prev.key === key) {
          return { key: key, dir: prev.dir === 'asc' ? 'desc' : 'asc' };
        }
        return { key: key, dir: 'asc' };
      });
    }

    function setFilter(key, v) {
      setFilters(function(prev) {
        var next = {};
        for (var k in prev) next[k] = prev[k];
        next[key] = v;
        return next;
      });
    }

    var displayed = useMemo(function() {
      var out = rows.slice();
      // filter
      for (var k in filters) {
        var f = (filters[k] || '').toLowerCase().trim();
        if (!f) continue;
        out = out.filter(function(r) {
          var v = r[k];
          return v !== undefined && v !== null &&
            String(v).toLowerCase().indexOf(f) !== -1;
        });
      }
      // sort
      if (sort) {
        out.sort(function(a, b) {
          var av = a[sort.key]; var bv = b[sort.key];
          if (av === bv) return 0;
          if (av === null || av === undefined) return 1;
          if (bv === null || bv === undefined) return -1;
          var cmp = (typeof av === 'number' && typeof bv === 'number')
            ? (av - bv)
            : String(av).localeCompare(String(bv));
          return sort.dir === 'asc' ? cmp : -cmp;
        });
      }
      return out;
    }, [rows, filters, sort]);

    return e('div', { className: 'overflow-x-auto' },
      e('table', null,
        e('thead', null,
          e('tr', null, columns.map(function(c) {
            var ariaSort = 'none';
            if (sort && sort.key === c.key) {
              ariaSort = sort.dir === 'asc' ? 'ascending' : 'descending';
            }
            return e('th', {
              key: c.key,
              scope: 'col',
              'aria-sort': ariaSort,
              onClick: function() { clickHeader(c.key); },
              title: 'Click to sort',
            }, c.label,
              sort && sort.key === c.key ? ' ' + (sort.dir === 'asc' ? '\u2191' : '\u2193') : ''
            );
          })),
          e('tr', null, columns.map(function(c) {
            return e('th', { key: 'f-' + c.key, style: { background: 'var(--bg)', cursor: 'default' } },
              e('input', {
                type: 'text',
                className: 'filter-input',
                placeholder: 'filter',
                value: filters[c.key] || '',
                onChange: function(ev) { setFilter(c.key, ev.target.value); },
                'aria-label': 'Filter ' + c.label,
              })
            );
          }))
        ),
        e('tbody', null, displayed.map(function(r, i) {
          return e('tr', { key: r._key || i }, columns.map(function(c) {
            var v = r[c.key];
            if (c.render) return e('td', { key: c.key, className: c.mono ? 'mono' : '' }, c.render(r));
            return e('td', { key: c.key, className: c.mono ? 'mono' : '' }, v == null ? '' : String(v));
          }));
        }))
      )
    );
  }

  // Collapsible panel wrapper.
  function Collapsible(props) {
    var _open = useState(true);
    var open = _open[0]; var setOpen = _open[1];
    return e('div', null,
      e(CardHeader, null,
        e(CardTitle, { num: props.num, id: props.titleId }, props.title),
        e(Button, {
          onClick: function() { setOpen(function(v) { return !v; }); },
          title: open ? 'Collapse' : 'Expand',
        }, open ? 'Collapse' : 'Expand')
      ),
      open ? props.children : null
    );
  }

  // SVG bar chart for framework coverage.
  function CoverageChart(props) {
    var data = props.data || [];
    if (data.length === 0) {
      return e('p', { className: 'text-dim font-display text-sm' }, 'No coverage data.');
    }
    return e('div', { className: 'flex flex-col gap-3' }, data.map(function(d) {
      var pct = Math.max(0, Math.min(100, d.pct));
      return e('div', { key: d.label, className: 'flex items-center gap-3' },
        e('span', { className: 'font-display text-sm text-dim', style: { minWidth: 120 } }, d.label),
        e('div', { className: 'bar-track' },
          e('div', { className: 'bar-fill', style: { width: pct.toFixed(1) + '%' } })
        ),
        e('span', { className: 'font-display text-sm', style: { minWidth: 48, textAlign: 'right' } }, pct.toFixed(0) + '%')
      );
    }));
  }

  // SVG donut for EU AI Act tier distribution.
  function TierDonut(props) {
    var data = props.data || [];
    var total = data.reduce(function(s, d) { return s + d.count; }, 0);
    if (total === 0) {
      return e('p', { className: 'text-dim font-display text-sm' }, 'No classification data.');
    }
    var size = 160; var r = 60; var cx_ = size / 2; var cy = size / 2;
    var cum = 0;
    var slices = data.filter(function(d) { return d.count > 0; }).map(function(d) {
      var frac = d.count / total;
      var start = cum * 2 * Math.PI; cum += frac;
      var end = cum * 2 * Math.PI;
      var x1 = cx_ + r * Math.sin(start); var y1 = cy - r * Math.cos(start);
      var x2 = cx_ + r * Math.sin(end); var y2 = cy - r * Math.cos(end);
      var large = frac > 0.5 ? 1 : 0;
      var path = 'M ' + cx_ + ' ' + cy + ' L ' + x1 + ' ' + y1 +
                 ' A ' + r + ' ' + r + ' 0 ' + large + ' 1 ' + x2 + ' ' + y2 + ' Z';
      return e('path', {
        key: d.tier, d: path, fill: d.color, stroke: 'var(--bg)', strokeWidth: 2,
      });
    });
    var legend = data.filter(function(d) { return d.count > 0; }).map(function(d) {
      return e('li', {
        key: d.tier,
        className: 'flex items-center gap-2 font-display text-xs',
      },
        e('span', { style: {
          display: 'inline-block', width: 10, height: 10, background: d.color, borderRadius: 2,
        }}),
        e('span', { className: 'text-dim' }, d.tier.replace(/-/g, ' '), ': '),
        e('span', { className: 'text-text' }, d.count)
      );
    });
    return e('div', { className: 'flex items-center gap-6' },
      e('svg', { width: size, height: size, 'aria-label': 'EU AI Act tier donut' },
        e('circle', { cx: cx_, cy: cy, r: r, fill: 'var(--surface-2)' }),
        slices,
        e('circle', { cx: cx_, cy: cy, r: r * 0.55, fill: 'var(--surface)' }),
        e('text', {
          x: cx_, y: cy + 4, textAnchor: 'middle',
          className: 'font-display', fill: 'var(--text)', fontSize: 14,
        }, total)
      ),
      e('ul', { className: 'flex flex-col gap-2 m-0 p-0', style: { listStyle: 'none' } }, legend)
    );
  }

  // ------------------------------------------------------------------
  // Panels
  // ------------------------------------------------------------------

  function TileRow(props) {
    return e('div', { className: 'grid grid-cols-auto-fit gap-3 mt-2' },
      props.tiles.map(function(t, i) {
        return e('div', {
          key: i,
          className: 'bg-surface-2 border rounded p-4 flex flex-col gap-1',
        },
          e('span', {
            className: cx(
              'font-display font-medium text-2xl leading-tight',
              t.tone === 'accent' ? 'text-accent' :
              t.tone === 'ok' ? 'text-ok' :
              t.tone === 'warn' ? 'text-warn' :
              t.tone === 'danger' ? 'text-danger' : 'text-text'
            ),
          }, String(t.count)),
          e('span', {
            className: 'font-display text-xs uppercase tracking-wide text-dim',
          }, t.label),
          t.href ? e('a', {
            href: t.href,
            className: 'font-display text-xs text-faint',
          }, 'view source') : null
        );
      })
    );
  }

  function CopyButton(props) {
    var _copied = useState(false);
    var copied = _copied[0]; var setCopied = _copied[1];
    function onClick() {
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(props.value);
        }
      } catch (err) { /* ignore */ }
      setCopied(true);
      setTimeout(function() { setCopied(false); }, 1500);
    }
    return e(Button, {
      onClick: onClick,
      title: 'Copy artifact URL: ' + props.value,
    }, copied ? 'Copied' : 'Copy');
  }

  function PanelRisk(props) {
    var d = props.data || {};
    var tiles = [
      { count: d.total || 0, label: 'Total rows', tone: 'accent', href: d.source },
      { count: (d.by_tier && d.by_tier.high) || 0, label: 'Tier: high', tone: 'danger' },
      { count: (d.by_tier && d.by_tier.medium) || 0, label: 'Tier: medium', tone: 'warn' },
      { count: (d.by_tier && d.by_tier.low) || 0, label: 'Tier: low' },
      { count: (d.by_treatment && d.by_treatment.reduce) || 0, label: 'Treat: reduce', tone: 'accent' },
      { count: (d.by_treatment && d.by_treatment.accept) || 0, label: 'Treat: accept', tone: 'ok' },
    ];
    return e(Card, { jurisdiction: 'global', titleId: 'p-risk' },
      e(Collapsible, { num: '01', title: 'Risk register', titleId: 'p-risk' },
        e(CardContent, null, e(TileRow, { tiles: tiles }))
      )
    );
  }

  function PanelSoa(props) {
    var d = props.data || {};
    var statuses = [
      'included-implemented', 'included-planned', 'included-partial',
      'excluded-not-applicable', 'excluded-risk-accepted',
    ];
    var tiles = statuses.map(function(s) {
      return {
        count: (d.by_status && d.by_status[s]) || 0,
        label: s.replace(/-/g, ' '),
        tone: s === 'included-implemented' ? 'ok' : (s.indexOf('included') === 0 ? 'accent' : ''),
        href: d.source,
      };
    });
    return e(Card, { jurisdiction: 'global', titleId: 'p-soa' },
      e(Collapsible, { num: '02', title: 'Statement of Applicability', titleId: 'p-soa' },
        e(CardContent, null, e(TileRow, { tiles: tiles }))
      )
    );
  }

  function PanelAisia(props) {
    var d = props.data || {};
    var tiles = [
      { count: d.complete || 0, label: 'Complete', tone: 'ok', href: d.source },
      { count: d.with_gaps || 0, label: 'With gaps', tone: 'warn' },
      { count: d.systems || 0, label: 'Systems assessed', tone: 'accent' },
    ];
    return e(Card, { jurisdiction: 'global', titleId: 'p-aisia' },
      e(Collapsible, { num: '03', title: 'AISIA coverage', titleId: 'p-aisia' },
        e(CardContent, null, e(TileRow, { tiles: tiles }))
      )
    );
  }

  function PanelNc(props) {
    var d = props.data || {};
    var tiles = [
      { count: d.open || 0, label: 'Open', tone: 'warn', href: d.source },
      { count: d.in_progress || 0, label: 'In progress', tone: 'accent' },
      { count: d.closed || 0, label: 'Closed', tone: 'ok' },
      { count: (d.median_age_days || 0).toFixed(0) + 'd', label: 'Median age (open)' },
    ];
    return e(Card, { jurisdiction: 'global', titleId: 'p-nc' },
      e(Collapsible, { num: '04', title: 'Nonconformity', titleId: 'p-nc' },
        e(CardContent, null, e(TileRow, { tiles: tiles }))
      )
    );
  }

  function PanelKpi(props) {
    var d = props.data || {};
    var tiles = [
      { count: d.breaches || 0, label: 'Breaches', tone: d.breaches ? 'danger' : 'ok', href: d.source },
      { count: d.total || 0, label: 'KPIs tracked', tone: 'accent' },
    ];
    return e(Card, { jurisdiction: 'global', titleId: 'p-kpi' },
      e(Collapsible, { num: '05', title: 'KPI posture', titleId: 'p-kpi' },
        e(CardContent, null, e(TileRow, { tiles: tiles }))
      )
    );
  }

  function PanelGap(props) {
    var d = props.data || {};
    return e(Card, { jurisdiction: 'global', titleId: 'p-gap' },
      e(Collapsible, { num: '06', title: 'Gap assessment', titleId: 'p-gap' },
        e(CardContent, null,
          e(CoverageChart, { data: d.frameworks || [] })
        )
      )
    );
  }

  function PanelEu(props) {
    var d = props.data || {};
    var tiers = d.tiers || [];
    var TIER_COLORS = {
      'prohibited': 'var(--danger)',
      'high-risk-annex-i': 'var(--danger)',
      'high-risk-annex-iii': 'var(--warn)',
      'limited-risk': 'var(--accent)',
      'minimal-risk': 'var(--ok)',
      'requires-legal-review': 'var(--warn)',
    };
    var donutData = tiers.map(function(t) {
      return { tier: t.tier, count: t.count, color: TIER_COLORS[t.tier] || 'var(--text-dim)' };
    });
    return e(Card, { jurisdiction: 'eu', className: '', titleId: 'p-eu' },
      e(Collapsible, { num: '07', title: 'EU AI Act classification', titleId: 'p-eu' },
        e(CardContent, null, e(TierDonut, { data: donutData }))
      )
    );
  }

  function PanelUsaStates(props) {
    var rows = (props.data && props.data.rows) || [];
    var columns = [
      { key: 'state', label: 'State' },
      { key: 'framework', label: 'Framework' },
      { key: 'count', label: 'Records', mono: true, render: function(r) {
        if (r.count > 0 && r.href) {
          return e('a', { href: r.href }, String(r.count));
        }
        return e('span', { className: 'mono' }, String(r.count));
      } },
      { key: 'latest', label: 'Latest', mono: true, render: function(r) {
        if (r.latest && r.latest_href) {
          return e('a', { href: r.latest_href }, r.latest);
        }
        return e('span', { className: 'mono' }, r.latest || '-');
      } },
    ];
    return e(Card, { jurisdiction: 'usa-states', titleId: 'p-usa' },
      e(Collapsible, { num: '08', title: 'USA state-level activity', titleId: 'p-usa' },
        e(CardContent, null,
          e(DataTable, { columns: columns, rows: rows.map(function(r, i) { r._key = i; return r; }) })
        )
      )
    );
  }

  function PanelUk(props) {
    var rows = (props.data && props.data.rows) || [];
    if (rows.length === 0) {
      return e(Card, { jurisdiction: 'uk', titleId: 'p-uk' },
        e(Collapsible, { num: '10', title: 'UK ATRS records', titleId: 'p-uk' },
          e(CardContent, null, e('p', { className: 'text-dim font-display text-sm' }, 'No UK ATRS records.'))
        )
      );
    }
    var columns = [
      { key: 'title', label: 'System' },
      { key: 'status', label: 'Status', render: function(r) {
        return e(Badge, { tone: 'accent' }, r.status);
      } },
      { key: 'href', label: 'Source', render: function(r) {
        return e('span', { className: 'flex items-center gap-2' },
          e('a', { href: r.href }, 'open'),
          e(CopyButton, { value: r.href })
        );
      } },
    ];
    return e(Card, { jurisdiction: 'uk', titleId: 'p-uk' },
      e(Collapsible, { num: '10', title: 'UK ATRS records', titleId: 'p-uk' },
        e(CardContent, null,
          e(DataTable, { columns: columns, rows: rows.map(function(r, i) { r._key = i; return r; }) })
        )
      )
    );
  }

  function PanelAction(props) {
    var rows = (props.data && props.data.rows) || [];
    if (rows.length === 0) {
      return e(Card, { jurisdiction: 'global', titleId: 'p-act' },
        e(Collapsible, { num: '09', title: 'Action required: human', titleId: 'p-act' },
          e(CardContent, null, e('p', { className: 'text-dim font-display text-sm' }, 'No items flagged for human action.'))
        )
      );
    }
    var columns = [
      { key: 'title', label: 'Item' },
      { key: 'reason', label: 'Flag', render: function(r) {
        return e(Badge, { tone: 'warn' }, r.reason);
      } },
      { key: 'href', label: 'Source', render: function(r) {
        return e('span', { className: 'flex items-center gap-2' },
          e('a', { href: r.href }, 'open'),
          e(CopyButton, { value: r.href })
        );
      } },
    ];
    return e(Card, { jurisdiction: 'global', titleId: 'p-act' },
      e(Collapsible, { num: '09', title: 'Action required: human', titleId: 'p-act' },
        e(CardContent, null,
          e(DataTable, { columns: columns, rows: rows.map(function(r, i) { r._key = i; return r; }) })
        )
      )
    );
  }

  function Provenance(props) {
    var rows = (props.data && props.data.rows) || [];
    if (rows.length === 0) {
      return e('footer', { className: 'mt-8 pt-6 border-t font-display text-sm text-dim' },
        e('h2', { className: 'text-sm mb-3' }, 'Provenance: AGENT_SIGNATURE per artifact type'),
        e('p', null, 'no artifacts')
      );
    }
    return e('footer', { className: 'mt-8 pt-6 border-t font-display text-sm text-dim' },
      e('h2', { className: 'text-sm mb-3' }, 'Provenance: AGENT_SIGNATURE per artifact type'),
      e('ul', { className: 'flex flex-col gap-1 m-0 p-0', style: { listStyle: 'none' } },
        rows.map(function(r, i) {
          return e('li', {
            key: i,
            className: 'flex justify-between gap-4 py-1 border-b',
            style: { borderBottomStyle: 'dashed' },
          },
            e('span', null, r.type),
            e('span', { className: 'text-faint break-all' }, r.signature),
            e('span', null, e('a', { href: r.href }, r.filename))
          );
        })
      )
    );
  }

  // ------------------------------------------------------------------
  // App shell
  // ------------------------------------------------------------------

  function filterByJurisdiction(jurisdiction) {
    // Hide panels whose data-jurisdiction is not compatible with the active view.
    var sections = document.querySelectorAll('section[data-jurisdiction]');
    sections.forEach(function(s) {
      var j = s.getAttribute('data-jurisdiction') || 'global';
      var show = true;
      if (jurisdiction === 'global') {
        show = true;
      } else if (jurisdiction === 'usa') {
        show = (j === 'global' || j === 'usa-states' || j.indexOf('usa') === 0);
      } else if (jurisdiction === 'eu') {
        show = (j === 'global' || j === 'eu');
      } else if (jurisdiction === 'uk') {
        show = (j === 'global' || j === 'uk');
      }
      s.style.display = show ? '' : 'none';
    });
  }

  function useKeyboardShortcuts(onSlash, onEscape) {
    useEffect(function() {
      function handler(ev) {
        if (ev.key === '/' && !(ev.target.tagName === 'INPUT' || ev.target.tagName === 'TEXTAREA')) {
          ev.preventDefault();
          onSlash();
        } else if (ev.key === 'Escape') {
          onEscape();
        }
      }
      window.addEventListener('keydown', handler);
      return function() { window.removeEventListener('keydown', handler); };
    }, [onSlash, onEscape]);
  }

  function App() {
    var STORAGE_KEY = 'aigovclaw.hub.v1.jurisdiction';
    var initial = 'global';
    try {
      var stored = sessionStorage.getItem(STORAGE_KEY);
      if (stored && ['global', 'usa', 'eu', 'uk'].indexOf(stored) !== -1) initial = stored;
    } catch (err) { /* ignore */ }

    var _j = useState(initial);
    var j = _j[0]; var setJ = _j[1];
    var _q = useState('');
    var q = _q[0]; var setQ = _q[1];
    var searchRef = useRef(null);

    useEffect(function() {
      filterByJurisdiction(j);
      try { sessionStorage.setItem(STORAGE_KEY, j); } catch (err) { /* ignore */ }
    }, [j]);

    useKeyboardShortcuts(
      function() { if (searchRef.current) searchRef.current.focus(); },
      function() { setQ(''); if (searchRef.current) searchRef.current.blur(); }
    );

    var tabs = [
      { value: 'global', label: 'Global' },
      { value: 'usa', label: 'USA' },
      { value: 'eu', label: 'EU' },
      { value: 'uk', label: 'UK' },
    ];

    var isEmpty = !DATA.has_any_artifacts;

    if (isEmpty) {
      return e('div', { className: 'max-w-screen mx-auto p-8' },
        e('header', { className: 'mb-8 pb-4 border-b' },
          e('span', { className: 'font-display text-xs uppercase tracking-wider text-accent' }, 'AIGovClaw Command Centre v1'),
          e('h1', { className: 'font-display font-medium text-3xl leading-tight mt-1' }, 'No evidence yet.')
        ),
        e(Alert, { tone: 'warn' },
          'The evidence store at this path is empty or missing: ', DATA.evidence_path || '(unspecified)'
        ),
        e('p', { className: 'text-dim mb-3' }, 'Run a plugin to produce your first artifact. For example:'),
        e('pre', { className: 'bg-surface border rounded p-4 font-display text-sm overflow-x-auto' },
          'hermes run aigovops.risk-register --input <path>\nhermes run aigovops.soa-maintenance\nhermes run aigovops.eu-ai-act-classifier'
        ),
        e('p', { className: 'text-dim mt-4' }, 'Then regenerate this Command Centre:'),
        e('pre', { className: 'bg-surface border rounded p-4 font-display text-sm overflow-x-auto' },
          'python3 -m aigovclaw.hub.v1.cli generate --output hub-v1.html'
        ),
        e('p', { className: 'font-display text-xs text-faint mt-8' }, 'Generated ', DATA.generated_at || '')
      );
    }

    return e('div', { className: 'max-w-screen mx-auto px-6 py-6' },
      e('a', { className: 'skip-link', href: '#main' }, 'Skip to content'),
      e('header', { className: 'flex justify-between items-end flex-wrap gap-4 mb-6 pb-4 border-b' },
        e('div', { className: 'flex flex-col gap-1' },
          e('span', { className: 'font-display text-xs uppercase tracking-wider text-accent' }, 'AIGovClaw Command Centre v1'),
          e('h1', { className: 'font-display font-medium text-3xl leading-tight' },
            'Composite ', e('span', { className: 'text-accent' }, '|'), ' AIMS state')
        ),
        e('div', { className: 'font-display text-sm text-dim text-right' },
          e('div', null, 'Generated ', DATA.generated_at || ''),
          e('div', { className: 'text-faint break-all' }, DATA.evidence_path || '')
        )
      ),
      e(Tabs, { items: tabs, value: j, onChange: setJ }),
      e('div', { className: 'flex items-center gap-2 mb-4' },
        e('input', {
          ref: searchRef,
          type: 'text',
          className: 'filter-input',
          placeholder: 'Global search (press / to focus, esc to clear)',
          value: q,
          onChange: function(ev) { setQ(ev.target.value); },
          'aria-label': 'Global search',
          style: { maxWidth: 420 },
        })
      ),
      e('main', { id: 'main' },
        e('div', { className: 'grid grid-cols-2 gap-6' },
          e(PanelRisk, { data: DATA.risk }),
          e(PanelSoa, { data: DATA.soa }),
          e(PanelAisia, { data: DATA.aisia }),
          e(PanelNc, { data: DATA.nonconformity }),
          e(PanelKpi, { data: DATA.kpi }),
          e(PanelGap, { data: DATA.gap })
        ),
        e('div', { className: 'mt-6' },
          e(PanelEu, { data: DATA.eu }),
          e(PanelUsaStates, { data: DATA.usa_states }),
          e(PanelUk, { data: DATA.uk }),
          e(PanelAction, { data: DATA.action_required })
        ),
        e(Provenance, { data: DATA.provenance })
      )
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
<meta name="generator" content="aigovclaw-hub/v1">
<meta name="color-scheme" content="dark">
<title>AIGovClaw Command Centre v1. Composite AIMS state.</title>
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
<script type="application/json" id="__AIGOVCLAW_HUB_DATA__">
{data_json}
</script>
<script>
// Parse inlined data payload.
(function() {{
  var el = document.getElementById('__AIGOVCLAW_HUB_DATA__');
  if (el) {{
    try {{ window.__AIGOVCLAW_HUB_DATA__ = JSON.parse(el.textContent); }}
    catch (err) {{ window.__AIGOVCLAW_HUB_DATA__ = {{}}; }}
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
    "FATAL: AIGovClaw Command Centre v1 requires vendored React bundles.\n"
    "Drop the following files into hub/v1/vendor/ and retry:\n"
    "  - hub/v1/vendor/react.production.min.js\n"
    "  - hub/v1/vendor/react-dom.production.min.js\n"
    "Source: https://unpkg.com/react@18/umd/react.production.min.js\n"
    "Source: https://unpkg.com/react-dom@18/umd/react-dom.production.min.js\n"
    "Download offline, verify the contents, then commit the files.\n"
    "No network fetch is performed by the generator."
)
