"""AIGovClaw Hub v1 generator.

Builds a single self-contained React + curated-Tailwind-subset + shadcn-shaped
HTML artifact from the same evidence store v0 reads.

v1 does NOT replace v0. v0 remains the default portable single-file output.
v1 is the richer interactive view: sortable filterable tables, collapsible
panels, SVG charts, keyboard shortcuts, jurisdiction tab bar. Same data, same
aesthetic bar, same read-only local-only threat model.

Stdlib Python only. Vendored React UMD bundles loaded from
hub/v1/vendor/. No network at generate time. No CDN at runtime.
"""

from __future__ import annotations

import json
import os
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..generator import (
    ARTIFACT_DIRS,
    SOA_STATUSES,
    EU_TIERS,
    US_STATE_ROWS,
    Store,
    resolve_evidence_path,
    _age_days,
    _count_by,
    _rel_from_base,
)
from .templates import (
    APP_JS,
    HTML_TEMPLATE,
    TAILWIND_SUBSET_CSS,
    VENDOR_MISSING_MESSAGE,
)


VENDOR_DIR = Path(__file__).parent / "vendor"
REACT_UMD_PATH = VENDOR_DIR / "react.production.min.js"
REACT_DOM_UMD_PATH = VENDOR_DIR / "react-dom.production.min.js"


class VendorMissingError(RuntimeError):
    """Raised when required vendor files are not present."""


# --------------------------------------------------------------------------
# Data extraction: condense the Store into a JSON-friendly payload.
# --------------------------------------------------------------------------


def _extract_risk(store: Store) -> dict:
    arts = store.artifacts.get("risk-register", [])
    rows: list[dict] = []
    for a in arts:
        r = a.data.get("rows") or a.data.get("risks")
        if isinstance(r, list):
            rows.extend([x for x in r if isinstance(x, dict)])
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
    return {
        "total": len(rows),
        "by_tier": by_tier,
        "by_treatment": by_treatment,
        "source": source,
    }


def _extract_soa(store: Store) -> dict:
    arts = store.artifacts.get("soa", [])
    rows: list[dict] = []
    for a in arts:
        r = a.data.get("rows") or a.data.get("controls")
        if isinstance(r, list):
            rows.extend([x for x in r if isinstance(x, dict)])
    by_status = _count_by(rows, "status")
    # Zero-fill canonical statuses.
    out = {s: by_status.get(s, 0) for s in SOA_STATUSES}
    source = arts[-1].rel_href if arts else None
    return {"by_status": out, "source": source}


def _extract_aisia(store: Store) -> dict:
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
    return {
        "complete": complete,
        "with_gaps": gaps,
        "systems": len(systems),
        "source": source,
    }


def _extract_nc(store: Store) -> dict:
    arts = store.artifacts.get("nonconformity", [])
    now = datetime.now(tz=timezone.utc)
    open_ages: list[float] = []
    IN_PROGRESS = {
        "investigated", "root-cause-identified", "corrective-action-planned",
        "corrective-action-in-progress", "effectiveness-reviewed",
    }
    CLOSED = {"closed"}
    counts = {"open": 0, "in_progress": 0, "closed": 0}
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
                counts["closed"] += 1
            elif status in IN_PROGRESS:
                counts["in_progress"] += 1
            else:
                counts["open"] += 1
                detected = rec.get("detected_at") or rec.get("created_at")
                if isinstance(detected, str):
                    d = _age_days(detected, now)
                    if d is not None:
                        open_ages.append(d)
    median_age = statistics.median(open_ages) if open_ages else 0
    return {
        "open": counts["open"],
        "in_progress": counts["in_progress"],
        "closed": counts["closed"],
        "median_age_days": median_age,
        "source": source,
    }


def _extract_kpi(store: Store) -> dict:
    arts = store.artifacts.get("metrics", [])
    breaches = 0
    total = 0
    source = arts[-1].rel_href if arts else None
    for a in arts:
        kpi_records = a.data.get("kpi_records") or a.data.get("kpis") or []
        if isinstance(kpi_records, list):
            total += sum(1 for k in kpi_records if isinstance(k, dict))
        tb = a.data.get("threshold_breaches") or []
        if isinstance(tb, list):
            breaches += sum(1 for k in tb if isinstance(k, dict))
    return {"breaches": breaches, "total": total, "source": source}


def _extract_gap(store: Store) -> dict:
    arts = store.artifacts.get("gap-assessment", [])
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
    frameworks = []
    for fw in ("ISO-42001", "NIST-AI-RMF", "EU-AI-Act"):
        scores = by_fw.get(fw, [])
        pct = (sum(scores) / len(scores) * 100.0) if scores else 0.0
        frameworks.append({"label": fw, "pct": pct})
    return {"frameworks": frameworks}


def _extract_eu(store: Store) -> dict:
    latest = store.latest_per("classification")
    counts = {t: 0 for t in EU_TIERS}
    for art in latest.values():
        t = art.data.get("risk_tier")
        if isinstance(t, str):
            counts[t] = counts.get(t, 0) + 1
    tiers = [{"tier": t, "count": counts.get(t, 0)} for t in EU_TIERS]
    return {"tiers": tiers}


def _extract_usa_states(store: Store) -> dict:
    rows = []
    for key, state_name, framework in US_STATE_ROWS:
        arts = store.artifacts.get(key, [])
        count = len(arts)
        latest_date = "-"
        latest_href = None
        href = None
        if count:
            latest = max(arts, key=lambda a: a.mtime)
            latest_date = latest.generated_at[:10]
            latest_href = latest.rel_href
            href = arts[0].rel_href
        rows.append({
            "state": state_name,
            "framework": framework,
            "count": count,
            "latest": latest_date,
            "href": href,
            "latest_href": latest_href,
        })
    return {"rows": rows}


def _extract_uk(store: Store) -> dict:
    arts = store.artifacts.get("uk-atrs", [])
    rows = []
    for a in arts[:50]:
        d = a.data
        rows.append({
            "title": d.get("title") or d.get("system_name") or a.path.stem,
            "status": d.get("status") or d.get("stage") or "recorded",
            "href": a.rel_href,
        })
    return {"rows": rows}


def _extract_action_required(store: Store) -> dict:
    arts = store.artifacts.get("action-required", [])
    rows = []
    for a in arts[:50]:
        d = a.data
        rows.append({
            "title": d.get("title") or d.get("summary") or a.path.stem,
            "reason": d.get("reason") or d.get("tag") or "action-required-human",
            "href": a.rel_href,
        })
    return {"rows": rows}


def _extract_provenance(store: Store) -> dict:
    rows = []
    for key in ARTIFACT_DIRS.keys():
        arts = store.artifacts.get(key, [])
        if not arts:
            continue
        latest = max(arts, key=lambda a: a.mtime)
        rows.append({
            "type": key,
            "signature": latest.agent_signature,
            "href": latest.rel_href,
            "filename": latest.path.name,
        })
    return {"rows": rows}


def build_payload(store: Store, *, generated_at: str) -> dict:
    """Build the JSON payload that the v1 React app consumes."""
    return {
        "generated_at": generated_at,
        "evidence_path": str(store.base),
        "has_any_artifacts": not store.is_empty(),
        "risk": _extract_risk(store),
        "soa": _extract_soa(store),
        "aisia": _extract_aisia(store),
        "nonconformity": _extract_nc(store),
        "kpi": _extract_kpi(store),
        "gap": _extract_gap(store),
        "eu": _extract_eu(store),
        "usa_states": _extract_usa_states(store),
        "uk": _extract_uk(store),
        "action_required": _extract_action_required(store),
        "provenance": _extract_provenance(store),
    }


# --------------------------------------------------------------------------
# Vendor loading
# --------------------------------------------------------------------------


def _load_vendor(path: Path) -> str:
    if not path.exists() or not path.is_file():
        raise VendorMissingError(VENDOR_MISSING_MESSAGE)
    text = path.read_text(encoding="utf-8")
    if len(text) < 1000:
        raise VendorMissingError(
            VENDOR_MISSING_MESSAGE
            + f"\n(File {path} exists but is too small to be a real UMD bundle.)"
        )
    return text


def _sanitize_for_inline(js: str) -> str:
    """Protect inlined JS from accidentally closing the host <script>.

    Embeds a benign zero-width split inside any literal '</script' occurrence.
    """
    return js.replace("</script", "<\\/script")


def _sanitize_json_for_inline(s: str) -> str:
    """Protect inlined JSON payload from HTML parser injection.

    The payload sits inside a <script type="application/json"> block. Any
    literal '</script' would close the block. Escape the '<' so it survives
    HTML parsing and JSON.parse at runtime.
    """
    return s.replace("</", "<\\/")


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------


def render(store: Store, *, generated_at: str | None = None) -> str:
    now = generated_at or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    payload = build_payload(store, generated_at=now)
    react_umd = _sanitize_for_inline(_load_vendor(REACT_UMD_PATH))
    react_dom_umd = _sanitize_for_inline(_load_vendor(REACT_DOM_UMD_PATH))
    data_json = _sanitize_json_for_inline(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))

    out = HTML_TEMPLATE.format(
        tailwind_css=TAILWIND_SUBSET_CSS,
        react_umd=react_umd,
        react_dom_umd=react_dom_umd,
        data_json=data_json,
        app_js=_sanitize_for_inline(APP_JS),
    )
    # Hard guard: no em-dashes in output.
    if "\u2014" in out:
        out = out.replace("\u2014", "--")
    return out


def generate(output_path: str | os.PathLike, evidence_path: str | os.PathLike | None = None) -> Path:
    base = resolve_evidence_path(evidence_path)
    store = Store.load(base)
    html_out = render(store)
    out = Path(output_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_out, encoding="utf-8")
    return out
