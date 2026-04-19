"""AIGovClaw Hub v0 generator.

Reads the local Hermes evidence store at ~/.hermes/memory/aigovclaw/ and emits
a single self-contained HTML dashboard.

Pure stdlib. No network. No third-party deps.

Artifact-type subdirectories recognized:
  - risk-register/
  - soa/                 (Statement of Applicability)
  - aisia/               (AI System Impact Assessment)
  - nonconformity/
  - metrics/             (KPI metrics-collector output)
  - gap-assessment/
  - classification/      (EU AI Act classifier output)
  - action-required/     (artifacts tagged action-required-human by the MCP router)

Each JSON file under a subdirectory is read once. For "latest per system"
aggregates the file with the greatest value of its 'generated_at' timestamp
(falling back to file mtime) wins for a given (type, system_id) tuple.
"""

from __future__ import annotations

import html
import json
import os
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .templates.layout import CSS, JURISDICTION_JS, empty_state


DEFAULT_EVIDENCE_PATH = Path.home() / ".hermes" / "memory" / "aigovclaw"

ARTIFACT_DIRS = {
    "risk-register": "risk-register",
    "soa": "soa",
    "aisia": "aisia",
    "nonconformity": "nonconformity",
    "metrics": "metrics",
    "gap-assessment": "gap-assessment",
    "classification": "classification",
    "action-required": "action-required",
    "uk-atrs": "uk-atrs",
    "colorado-ai-act": "colorado-ai-act",
    "nyc-ll144": "nyc-ll144",
    "california-ai": "california-ai",
}


# Fallback jurisdiction map for artifacts that do not carry a top-level
# "jurisdiction" field. Artifacts with the field override this map.
ARTIFACT_TYPE_DEFAULT_JURISDICTION = {
    "risk-register": "global",
    "soa": "global",
    "aisia": "global",
    "nonconformity": "global",
    "metrics": "global",
    "gap-assessment": "global",
    "classification": "eu",
    "action-required": "global",
    "uk-atrs": "uk",
    "colorado-ai-act": "usa-co",
    "nyc-ll144": "usa-nyc",
    "california-ai": "usa-ca",
}


def _artifact_jurisdiction(art: "Artifact", artifact_type: str) -> str:
    v = art.data.get("jurisdiction")
    if isinstance(v, str) and v:
        return v
    return ARTIFACT_TYPE_DEFAULT_JURISDICTION.get(artifact_type, "global")


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


@dataclass
class Artifact:
    path: Path
    data: dict
    mtime: float

    @property
    def rel_href(self) -> str:
        return self.path.as_posix()

    @property
    def generated_at(self) -> str:
        v = self.data.get("generated_at") or self.data.get("created_at")
        if isinstance(v, str):
            return v
        return datetime.fromtimestamp(self.mtime, tz=timezone.utc).isoformat()

    @property
    def agent_signature(self) -> str:
        v = self.data.get("AGENT_SIGNATURE") or self.data.get("agent_signature")
        if isinstance(v, str):
            return v
        return "unsigned"


def _walk_json(root: Path) -> Iterable[Artifact]:
    if not root.exists() or not root.is_dir():
        return []
    out: list[Artifact] = []
    for p in sorted(root.rglob("*.json")):
        try:
            with p.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        out.append(Artifact(path=p, data=data, mtime=p.stat().st_mtime))
    return out


@dataclass
class Store:
    base: Path
    artifacts: dict[str, list[Artifact]] = field(default_factory=dict)

    @classmethod
    def load(cls, base: Path) -> "Store":
        store = cls(base=base)
        for key, rel in ARTIFACT_DIRS.items():
            store.artifacts[key] = list(_walk_json(base / rel))
        return store

    def is_empty(self) -> bool:
        return all(len(v) == 0 for v in self.artifacts.values())

    def latest_per(self, key: str, id_field: str = "system_id") -> dict[str, Artifact]:
        latest: dict[str, Artifact] = {}
        for art in self.artifacts.get(key, []):
            sid = art.data.get(id_field) or art.path.stem
            cur = latest.get(sid)
            if cur is None or art.mtime > cur.mtime:
                latest[sid] = art
        return latest


# --------------------------------------------------------------------------
# Aggregation
# --------------------------------------------------------------------------


def _count_by(items: Iterable[Any], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in items:
        if isinstance(row, dict):
            v = row.get(key)
            if isinstance(v, str):
                out[v] = out.get(v, 0) + 1
    return out


def _age_days(iso_ts: str, now: datetime) -> float | None:
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).total_seconds() / 86400.0


# --------------------------------------------------------------------------
# Rendering helpers
# --------------------------------------------------------------------------


def e(s: Any) -> str:
    """HTML-escape. Also strips U+2014 em-dashes as a hard guard."""
    text = "" if s is None else str(s)
    text = text.replace("\u2014", "--")
    return html.escape(text, quote=True)


def _rel_from_base(base: Path, p: Path) -> str:
    try:
        return p.relative_to(base).as_posix()
    except ValueError:
        return p.as_posix()


def _tile(count: int | str, label: str, href: str | None = None, tone: str = "") -> str:
    tone_cls = f" {tone}" if tone else ""
    src = f'<a class="source" href="{e(href)}">view source</a>' if href else ""
    return (
        f'<div class="tile">'
        f'<span class="count{tone_cls}">{e(count)}</span>'
        f'<span class="label">{e(label)}</span>{src}'
        f'</div>'
    )


def _coverage_bar(label: str, pct: float) -> str:
    pct = max(0.0, min(100.0, pct))
    return (
        f'<div class="coverage-bar">'
        f'<span class="label">{e(label)}</span>'
        f'<div class="track"><div class="fill" style="width: {pct:.1f}%"></div></div>'
        f'<span class="value">{pct:.0f}%</span>'
        f'</div>'
    )


# --------------------------------------------------------------------------
# Panels
# --------------------------------------------------------------------------


def _panel_risk(store: Store) -> str:
    arts = store.artifacts.get("risk-register", [])
    rows: list[dict] = []
    for a in arts:
        # Primary key is "rows" per aigovops plugin contract; "risks" kept as fallback.
        r = a.data.get("rows") or a.data.get("risks")
        if isinstance(r, list):
            rows.extend([x for x in r if isinstance(x, dict)])
    # Derive tier from inherent_score when tier is not explicitly set:
    # >= 15 = high, 8-14 = medium, 1-7 = low. Matches common 5x5 heatmap.
    by_tier = {"high": 0, "medium": 0, "low": 0}
    by_treatment = {"reduce": 0, "accept": 0, "transfer": 0, "avoid": 0}
    for r in rows:
        tier = r.get("tier")
        if tier in by_tier:
            by_tier[tier] += 1
        else:
            score = r.get("inherent_score") or r.get("residual_score")
            if isinstance(score, (int, float)):
                if score >= 15:
                    by_tier["high"] += 1
                elif score >= 8:
                    by_tier["medium"] += 1
                else:
                    by_tier["low"] += 1
        t = r.get("treatment_option") or r.get("treatment")
        if t in by_treatment:
            by_treatment[t] += 1
    source = arts[-1].rel_href if arts else None
    tiles = [
        _tile(len(rows), "Total rows", href=source, tone="accent"),
        _tile(by_tier["high"], "Tier: high", tone="danger"),
        _tile(by_tier["medium"], "Tier: medium", tone="warn"),
        _tile(by_tier["low"], "Tier: low"),
        _tile(by_treatment["reduce"], "Treat: reduce", tone="accent"),
        _tile(by_treatment["accept"], "Treat: accept", tone="ok"),
    ]
    return (
        '<section class="panel" data-jurisdiction="global"><h2><span class="num">01</span>Risk register</h2>'
        f'<div class="tiles">{"".join(tiles)}</div></section>'
    )


SOA_STATUSES = [
    "included-implemented",
    "included-planned",
    "included-partial",
    "excluded-not-applicable",
    "excluded-risk-accepted",
]


def _panel_soa(store: Store) -> str:
    arts = store.artifacts.get("soa", [])
    rows: list[dict] = []
    for a in arts:
        # Primary key is "rows" per aigovops plugin contract; "controls" kept as fallback.
        r = a.data.get("rows") or a.data.get("controls")
        if isinstance(r, list):
            rows.extend([x for x in r if isinstance(x, dict)])
    by_status = _count_by(rows, "status")
    source = arts[-1].rel_href if arts else None
    tiles = []
    for s in SOA_STATUSES:
        count = by_status.get(s, 0)
        tone = "ok" if s == "included-implemented" else ("accent" if s.startswith("included") else "")
        tiles.append(_tile(count, s.replace("-", " "), href=source, tone=tone))
    return (
        '<section class="panel" data-jurisdiction="global"><h2><span class="num">02</span>Statement of Applicability</h2>'
        f'<div class="tiles">{"".join(tiles)}</div></section>'
    )


def _panel_aisia(store: Store) -> str:
    # One AISIA per system. "complete" = no warnings and no scaffold_sections.
    # "with gaps" = has warnings or scaffold_sections. "missing" = no aisia at all.
    arts = store.artifacts.get("aisia", [])
    complete = gaps = 0
    systems: set[str] = set()
    for a in arts:
        sid = a.data.get("system_name") or a.data.get("system_id") or a.path.stem
        systems.add(sid)
        has_gaps = bool(a.data.get("warnings")) or bool(a.data.get("scaffold_sections"))
        if has_gaps:
            gaps += 1
        else:
            complete += 1
    source = arts[-1].rel_href if arts else None
    tiles = [
        _tile(complete, "Complete", href=source, tone="ok"),
        _tile(gaps, "With gaps", tone="warn"),
        _tile(len(systems), "Systems assessed", tone="accent"),
    ]
    return (
        '<section class="panel" data-jurisdiction="global"><h2><span class="num">03</span>AISIA coverage</h2>'
        f'<div class="tiles">{"".join(tiles)}</div></section>'
    )


def _panel_nonconformity(store: Store) -> str:
    arts = store.artifacts.get("nonconformity", [])
    now = datetime.now(tz=timezone.utc)
    open_ages: list[float] = []
    # Nonconformity plugin uses an 8-stage lifecycle. Collapse to open / in-progress / closed for the tile view.
    IN_PROGRESS = {"investigated", "root-cause-identified", "corrective-action-planned",
                   "corrective-action-in-progress", "effectiveness-reviewed"}
    CLOSED = {"closed"}
    state_counts = {"open": 0, "in-progress": 0, "closed": 0}
    source = arts[-1].rel_href if arts else None
    for a in arts:
        records = a.data.get("records") or []
        if not isinstance(records, list):
            continue
        for rec in records:
            if not isinstance(rec, dict):
                continue
            status = rec.get("status") or rec.get("state") or "detected"
            if status in CLOSED:
                state_counts["closed"] += 1
            elif status in IN_PROGRESS:
                state_counts["in-progress"] += 1
            else:
                state_counts["open"] += 1
                detected = rec.get("detected_at") or rec.get("created_at")
                if isinstance(detected, str):
                    d = _age_days(detected, now)
                    if d is not None:
                        open_ages.append(d)
    median_age = statistics.median(open_ages) if open_ages else 0
    tiles = [
        _tile(state_counts["open"], "Open", href=source, tone="warn"),
        _tile(state_counts["in-progress"], "In progress", tone="accent"),
        _tile(state_counts["closed"], "Closed", tone="ok"),
        _tile(f"{median_age:.0f}d", "Median age (open)"),
    ]
    return (
        '<section class="panel" data-jurisdiction="global"><h2><span class="num">04</span>Nonconformity</h2>'
        f'<div class="tiles">{"".join(tiles)}</div></section>'
    )


def _panel_kpi(store: Store) -> str:
    arts = store.artifacts.get("metrics", [])
    breaches = 0
    total = 0
    source = arts[-1].rel_href if arts else None
    for a in arts:
        # Primary: kpi_records for total; threshold_breaches for breach count.
        kpi_records = a.data.get("kpi_records") or a.data.get("kpis") or []
        if isinstance(kpi_records, list):
            total += sum(1 for k in kpi_records if isinstance(k, dict))
        tb = a.data.get("threshold_breaches") or []
        if isinstance(tb, list):
            breaches += sum(1 for k in tb if isinstance(k, dict))
    tiles = [
        _tile(breaches, "Breaches", href=source, tone="danger" if breaches else "ok"),
        _tile(total, "KPIs tracked", tone="accent"),
    ]
    return (
        '<section class="panel" data-jurisdiction="global"><h2><span class="num">05</span>KPI posture</h2>'
        f'<div class="tiles">{"".join(tiles)}</div></section>'
    )


def _panel_gap(store: Store) -> str:
    arts = store.artifacts.get("gap-assessment", [])
    # Gap plugin uses target_framework + summary.coverage_score. Normalize fw keys.
    fw_aliases = {
        "iso42001": "ISO-42001", "iso-42001": "ISO-42001", "ISO-42001": "ISO-42001",
        "nist": "NIST-AI-RMF", "nist-ai-rmf": "NIST-AI-RMF", "NIST-AI-RMF": "NIST-AI-RMF",
        "eu-ai-act": "EU-AI-Act", "EU-AI-Act": "EU-AI-Act",
    }
    by_fw: dict[str, list[float]] = {}
    for a in arts:
        fw = a.data.get("target_framework") or a.data.get("framework")
        summary = a.data.get("summary") or {}
        score = summary.get("coverage_score") if isinstance(summary, dict) else None
        if score is None:
            score = a.data.get("coverage_score")
        if isinstance(fw, str) and isinstance(score, (int, float)):
            normalized = fw_aliases.get(fw, fw)
            by_fw.setdefault(normalized, []).append(float(score))
    bars = []
    for fw in ("ISO-42001", "NIST-AI-RMF", "EU-AI-Act"):
        scores = by_fw.get(fw, [])
        # coverage_score is 0.0-1.0 already; convert to percent.
        pct = (sum(scores) / len(scores) * 100.0) if scores else 0.0
        bars.append(_coverage_bar(fw, pct))
    return (
        '<section class="panel" data-jurisdiction="global"><h2><span class="num">06</span>Gap assessment</h2>'
        + "".join(bars)
        + '</section>'
    )


EU_TIERS = [
    "prohibited",
    "high-risk-annex-i",
    "high-risk-annex-iii",
    "limited-risk",
    "minimal-risk",
    "requires-legal-review",
]


def _panel_eu(store: Store) -> str:
    latest = store.latest_per("classification")
    counts = {t: 0 for t in EU_TIERS}
    for art in latest.values():
        t = art.data.get("risk_tier")
        if isinstance(t, str):
            counts[t] = counts.get(t, 0) + 1
    tiles = []
    for t in EU_TIERS:
        tone = {
            "prohibited": "danger",
            "high-risk-annex-i": "danger",
            "high-risk-annex-iii": "warn",
            "limited-risk": "accent",
            "minimal-risk": "ok",
            "requires-legal-review": "warn",
        }.get(t, "")
        tiles.append(_tile(counts.get(t, 0), t.replace("-", " "), tone=tone))
    return (
        '<section class="panel wide" data-jurisdiction="eu"><h2><span class="num">07</span>EU AI Act classification</h2>'
        f'<div class="tiles">{"".join(tiles)}</div></section>'
    )


def _panel_action_required(store: Store) -> str:
    arts = store.artifacts.get("action-required", [])
    if not arts:
        body = '<p style="color: var(--text-dim); font-family: var(--font-display); font-size: 13px;">No items flagged for human action.</p>'
    else:
        rows = []
        for a in arts[:20]:
            d = a.data
            title = d.get("title") or d.get("summary") or a.path.stem
            reason = d.get("reason") or d.get("tag") or "action-required-human"
            rows.append(
                f'<tr>'
                f'<td>{e(title)}</td>'
                f'<td><span class="badge warn">{e(reason)}</span></td>'
                f'<td><a href="{e(a.rel_href)}">open</a></td>'
                f'</tr>'
            )
        body = (
            '<table><thead><tr><th>Item</th><th>Flag</th><th>Source</th></tr></thead><tbody>'
            + "".join(rows)
            + '</tbody></table>'
        )
    return (
        '<section class="panel wide" data-jurisdiction="global"><h2><span class="num">09</span>Action required: human</h2>'
        + body
        + '</section>'
    )


US_STATE_ROWS = [
    ("colorado-ai-act", "Colorado", "SB 205"),
    ("nyc-ll144", "New York City", "Local Law 144"),
    ("california-ai", "California", "CPPA ADMT, CCPA, SB 942, AB 2013"),
]


def _panel_usa_states(store: Store) -> str:
    rows = []
    for key, state_name, framework in US_STATE_ROWS:
        arts = store.artifacts.get(key, [])
        count = len(arts)
        if count:
            latest = max(arts, key=lambda a: a.mtime)
            latest_cell = f'<a href="{e(latest.rel_href)}">{e(latest.generated_at[:10])}</a>'
            count_cell = f'<a href="{e(arts[0].rel_href)}">{count}</a>'
        else:
            latest_cell = '<span class="mono">-</span>'
            count_cell = '<span class="mono">0</span>'
        rows.append(
            '<tr>'
            f'<td>{e(state_name)}</td>'
            f'<td>{e(framework)}</td>'
            f'<td class="mono">{count_cell}</td>'
            f'<td class="mono">{latest_cell}</td>'
            '</tr>'
        )
    body = (
        '<table><thead><tr>'
        '<th>State</th><th>Framework</th><th>Records</th><th>Latest</th>'
        '</tr></thead><tbody>'
        + "".join(rows)
        + '</tbody></table>'
    )
    return (
        '<section class="panel wide" data-jurisdiction="usa-states">'
        '<h2><span class="num">08</span>USA state-level activity</h2>'
        + body
        + '</section>'
    )


def _panel_uk_atrs(store: Store) -> str:
    arts = store.artifacts.get("uk-atrs", [])
    if not arts:
        body = (
            '<p style="color: var(--text-dim); font-family: var(--font-display); '
            'font-size: 13px;">No UK ATRS records.</p>'
        )
    else:
        rows = []
        for a in arts[:20]:
            d = a.data
            title = d.get("title") or d.get("system_name") or a.path.stem
            status = d.get("status") or d.get("stage") or "recorded"
            rows.append(
                f'<tr>'
                f'<td>{e(title)}</td>'
                f'<td><span class="badge accent">{e(status)}</span></td>'
                f'<td><a href="{e(a.rel_href)}">open</a></td>'
                f'</tr>'
            )
        body = (
            '<table><thead><tr><th>System</th><th>Status</th><th>Source</th></tr></thead><tbody>'
            + "".join(rows)
            + '</tbody></table>'
        )
    return (
        '<section class="panel wide" data-jurisdiction="uk">'
        '<h2><span class="num">10</span>UK ATRS records</h2>'
        + body
        + '</section>'
    )


def _jurisdiction_bar() -> str:
    tabs = [
        ("global", "Global"),
        ("usa", "USA"),
        ("eu", "EU"),
        ("uk", "UK"),
    ]
    items = []
    for i, (key, label) in enumerate(tabs):
        selected = "true" if key == "global" else "false"
        tabindex = "0" if key == "global" else "-1"
        items.append(
            f'<li><button type="button" role="tab" '
            f'class="jurisdiction-tab" '
            f'data-jurisdiction="{e(key)}" '
            f'id="jtab-{e(key)}" '
            f'aria-selected="{selected}" '
            f'tabindex="{tabindex}">{e(label)}</button></li>'
        )
    return (
        '<nav class="jurisdiction-bar" aria-label="Jurisdiction filter">'
        '<ul class="jurisdiction-tabs" role="tablist" '
        'aria-label="Jurisdiction">'
        + "".join(items)
        + '</ul></nav>'
    )


def _footer_provenance(store: Store) -> str:
    rows = []
    for key in ARTIFACT_DIRS.keys():
        arts = store.artifacts.get(key, [])
        if not arts:
            continue
        latest = max(arts, key=lambda a: a.mtime)
        rows.append(
            f'<div class="row">'
            f'<span>{e(key)}</span>'
            f'<span class="sig">{e(latest.agent_signature)}</span>'
            f'<span><a href="{e(latest.rel_href)}">{e(latest.path.name)}</a></span>'
            f'</div>'
        )
    if not rows:
        rows = ['<div class="row"><span>no artifacts</span></div>']
    return (
        '<footer class="provenance"><h2>Provenance: AGENT_SIGNATURE per artifact type</h2>'
        + "".join(rows)
        + '</footer>'
    )


# --------------------------------------------------------------------------
# Top-level render
# --------------------------------------------------------------------------


def render(store: Store, *, generated_at: str | None = None) -> str:
    now = generated_at or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if store.is_empty():
        return empty_state(str(store.base), now)

    panels_top = [
        _panel_risk(store),
        _panel_soa(store),
        _panel_aisia(store),
        _panel_nonconformity(store),
        _panel_kpi(store),
        _panel_gap(store),
    ]
    panels_wide = [
        _panel_eu(store),
        _panel_usa_states(store),
        _panel_uk_atrs(store),
        _panel_action_required(store),
    ]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="aigovclaw-hub/v0">
<meta name="color-scheme" content="dark">
<title>AIGovClaw Command Centre. Composite AIMS state.</title>
<style>{CSS}</style>
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<div class="wrap">
  <header class="masthead">
    <div class="brand">
      <span class="eyebrow">AIGovClaw Command Centre v0</span>
      <h1>Composite <span class="pipe">|</span> AIMS state</h1>
    </div>
    <div class="meta">
      <div>Generated {e(now)}</div>
      <div class="path">{e(str(store.base))}</div>
    </div>
  </header>
  {_jurisdiction_bar()}
  <main id="main">
    <div class="grid">
      {"".join(panels_top)}
    </div>
    <div class="grid">
      {"".join(panels_wide)}
    </div>
    {_footer_provenance(store)}
  </main>
</div>
<script>{JURISDICTION_JS}</script>
</body>
</html>
"""


# --------------------------------------------------------------------------
# Public entry
# --------------------------------------------------------------------------


def resolve_evidence_path(override: str | os.PathLike | None = None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    env = os.environ.get("AIGOVCLAW_EVIDENCE_PATH")
    if env:
        return Path(env).expanduser().resolve()
    return DEFAULT_EVIDENCE_PATH


def generate(output_path: str | os.PathLike, evidence_path: str | os.PathLike | None = None) -> Path:
    base = resolve_evidence_path(evidence_path)
    store = Store.load(base)
    html_out = render(store)
    # Hard guard: no em-dashes in output.
    if "\u2014" in html_out:
        html_out = html_out.replace("\u2014", "--")
    out = Path(output_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_out, encoding="utf-8")
    return out
