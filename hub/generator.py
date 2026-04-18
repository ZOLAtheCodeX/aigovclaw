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
  - jules/flagged/       (FlaggedIssue records, active)
  - jules/archive/       (FlaggedIssue records, closed)
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

from .templates.layout import CSS, empty_state


DEFAULT_EVIDENCE_PATH = Path.home() / ".hermes" / "memory" / "aigovclaw"

ARTIFACT_DIRS = {
    "risk-register": "risk-register",
    "soa": "soa",
    "aisia": "aisia",
    "nonconformity": "nonconformity",
    "metrics": "metrics",
    "gap-assessment": "gap-assessment",
    "classification": "classification",
    "jules-flagged": "jules/flagged",
    "jules-archive": "jules/archive",
    "action-required": "action-required",
}


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
        r = a.data.get("risks")
        if isinstance(r, list):
            rows.extend([x for x in r if isinstance(x, dict)])
        elif isinstance(a.data, dict) and "tier" in a.data:
            rows.append(a.data)
    by_tier = _count_by(rows, "tier")
    by_status = _count_by(rows, "status")
    source = arts[-1].rel_href if arts else None
    tiles = [
        _tile(len(rows), "Total rows", href=source, tone="accent"),
        _tile(by_tier.get("high", 0), "Tier: high", tone="danger"),
        _tile(by_tier.get("medium", 0), "Tier: medium", tone="warn"),
        _tile(by_tier.get("low", 0), "Tier: low"),
        _tile(by_status.get("open", 0), "Status: open", tone="warn"),
        _tile(by_status.get("mitigated", 0), "Status: mitigated", tone="ok"),
    ]
    return (
        '<section class="panel"><h2><span class="num">01</span>Risk register</h2>'
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
        r = a.data.get("controls")
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
        '<section class="panel"><h2><span class="num">02</span>Statement of Applicability</h2>'
        f'<div class="tiles">{"".join(tiles)}</div></section>'
    )


def _panel_aisia(store: Store) -> str:
    latest = store.latest_per("aisia")
    complete = gaps = missing = 0
    links: dict[str, str] = {}
    for sid, art in latest.items():
        state = art.data.get("state") or art.data.get("status")
        if state == "complete":
            complete += 1
        elif state == "gaps":
            gaps += 1
        else:
            missing += 1
        links[sid] = art.rel_href
    tiles = [
        _tile(complete, "Complete", tone="ok"),
        _tile(gaps, "With gaps", tone="warn"),
        _tile(missing, "Missing", tone="danger"),
        _tile(len(latest), "Systems total", tone="accent"),
    ]
    return (
        '<section class="panel"><h2><span class="num">03</span>AISIA coverage</h2>'
        f'<div class="tiles">{"".join(tiles)}</div></section>'
    )


def _panel_nonconformity(store: Store) -> str:
    arts = store.artifacts.get("nonconformity", [])
    now = datetime.now(tz=timezone.utc)
    open_ages: list[float] = []
    state_counts = {"open": 0, "in-progress": 0, "closed": 0}
    source = arts[-1].rel_href if arts else None
    for a in arts:
        state = a.data.get("state") or "open"
        if state in state_counts:
            state_counts[state] += 1
        else:
            state_counts.setdefault(state, 0)
            state_counts[state] += 1
        if state == "open":
            created = a.data.get("created_at") or a.data.get("generated_at")
            if isinstance(created, str):
                d = _age_days(created, now)
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
        '<section class="panel"><h2><span class="num">04</span>Nonconformity</h2>'
        f'<div class="tiles">{"".join(tiles)}</div></section>'
    )


def _panel_kpi(store: Store) -> str:
    arts = store.artifacts.get("metrics", [])
    breaches = 0
    total = 0
    source = arts[-1].rel_href if arts else None
    for a in arts:
        kpis = a.data.get("kpis")
        if isinstance(kpis, list):
            for k in kpis:
                if not isinstance(k, dict):
                    continue
                total += 1
                if k.get("breach") is True or k.get("status") == "breach":
                    breaches += 1
    tiles = [
        _tile(breaches, "Breaches", href=source, tone="danger" if breaches else "ok"),
        _tile(total, "KPIs tracked", tone="accent"),
    ]
    return (
        '<section class="panel"><h2><span class="num">05</span>KPI posture</h2>'
        f'<div class="tiles">{"".join(tiles)}</div></section>'
    )


def _panel_gap(store: Store) -> str:
    arts = store.artifacts.get("gap-assessment", [])
    by_fw: dict[str, list[float]] = {}
    for a in arts:
        fw = a.data.get("framework")
        score = a.data.get("coverage_score")
        if isinstance(fw, str) and isinstance(score, (int, float)):
            by_fw.setdefault(fw, []).append(float(score))
    bars = []
    for fw in ("ISO-42001", "NIST-AI-RMF", "EU-AI-Act"):
        scores = by_fw.get(fw) or by_fw.get(fw.replace("-", "/")) or []
        pct = (sum(scores) / len(scores)) if scores else 0.0
        bars.append(_coverage_bar(fw, pct))
    return (
        '<section class="panel"><h2><span class="num">06</span>Gap assessment</h2>'
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
        '<section class="panel wide"><h2><span class="num">07</span>EU AI Act classification</h2>'
        f'<div class="tiles">{"".join(tiles)}</div></section>'
    )


def _panel_jules(store: Store) -> str:
    combined = list(store.artifacts.get("jules-flagged", [])) + list(
        store.artifacts.get("jules-archive", [])
    )
    combined.sort(key=lambda a: a.mtime, reverse=True)
    recent = combined[:10]
    if not recent:
        body = '<p style="color: var(--text-dim); font-family: var(--font-display); font-size: 13px;">No Jules activity recorded.</p>'
    else:
        rows = []
        for a in recent:
            d = a.data
            playbook = d.get("playbook", "")
            state = d.get("state", "")
            repo = d.get("target_repo", "")
            pr_url = d.get("pr_url") or d.get("pull_request_url") or ""
            pr_cell = (
                f'<a href="{e(pr_url)}">PR</a>' if pr_url.startswith("https://github.com") else e(pr_url)
            )
            rows.append(
                f'<tr>'
                f'<td class="mono">{e(playbook)}</td>'
                f'<td><span class="badge">{e(state)}</span></td>'
                f'<td class="mono">{e(repo)}</td>'
                f'<td class="mono">{pr_cell}</td>'
                f'<td><a href="{e(a.rel_href)}">source</a></td>'
                f'</tr>'
            )
        body = (
            '<table><thead><tr>'
            '<th>Playbook</th><th>State</th><th>Target</th><th>PR</th><th>Source</th>'
            '</tr></thead><tbody>'
            + "".join(rows)
            + '</tbody></table>'
        )
    return (
        '<section class="panel wide"><h2><span class="num">08</span>Recent Jules activity</h2>'
        + body
        + '</section>'
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
        '<section class="panel wide"><h2><span class="num">09</span>Action required: human</h2>'
        + body
        + '</section>'
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
        _panel_jules(store),
        _panel_action_required(store),
    ]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="aigovclaw-hub/v0">
<meta name="color-scheme" content="dark">
<title>AIGovClaw Hub. Composite AIMS state.</title>
<style>{CSS}</style>
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<div class="wrap">
  <header class="masthead">
    <div class="brand">
      <span class="eyebrow">AIGovClaw hub v0</span>
      <h1>Composite <span class="pipe">|</span> AIMS state</h1>
    </div>
    <div class="meta">
      <div>Generated {e(now)}</div>
      <div class="path">{e(str(store.base))}</div>
    </div>
  </header>
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
