"""Deterministic drift / conclusion-change detection.

Inputs:
    baseline aggregate  (data/aggregate/latest.json or 2026-05.json)
    current metrics     (work/metrics.json, full panel incl. per-player values)
    conclusions config  (config/conclusions.yaml)

Output:
    DriftReport with level 0/1/2, changed metrics, cohort change, and
    matched-panel change (roster composition vs same-player change separated).

No LLM anywhere in this module: rules are purely deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import yaml

from .metrics import metric_path

DEFAULT_CONCLUSIONS_PATH = "config/conclusions.yaml"


@dataclass
class DriftReport:
    level: int
    changed_metrics: list[dict] = field(default_factory=list)
    cohort_change: dict = field(default_factory=dict)
    matched_panel_change: dict = field(default_factory=dict)
    baseline_snapshot_date: Optional[str] = None
    current_snapshot_date: Optional[str] = None
    scope_changed: bool = False
    scope_warning: str = ""
    cohort_stability: str = "unavailable"  # stable | unstable | unavailable
    roster_turnover_rate: Optional[float] = None
    headline_suppressed: bool = False
    suppression_reason: str = ""
    series_compatible: bool = True
    baseline_incompatible_reason: str = ""


def load_conclusions(path: str = DEFAULT_CONCLUSIONS_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _pp_change(baseline: Optional[float], current: Optional[float]) -> Optional[float]:
    """Percentage-point change: (current - baseline) * 100."""
    if baseline is None or current is None:
        return None
    return round((current - baseline) * 100, 2)


def _band_change(baseline_agg: dict, current: float, baseline: float) -> bool:
    """True when the current value left the baseline's dominant band.

    Band = the eDPI distribution bin containing the baseline median.
    Not definable -> False (Level 1 only).
    """
    dist = (baseline_agg.get("edpi") or {}).get("distribution") or {}
    current_bin = None
    for label, lo, hi in _BIN_RANGES:
        if lo <= current < hi:
            current_bin = label
            break
    baseline_bin = None
    for label, lo, hi in _BIN_RANGES:
        if lo <= baseline < hi:
            baseline_bin = label
            break
    if baseline_bin is None or baseline_bin not in dist:
        return False  # band not definable -> Level 1 only
    return current_bin != baseline_bin


_BIN_RANGES = [
    ("0-400", 0, 400), ("400-600", 400, 600), ("600-800", 600, 800),
    ("800-1000", 800, 1000), ("1000-1200", 1000, 1200), ("1200-1600", 1200, 1600),
    ("1600+", 1600, float("inf")),
]


def _evaluate_conclusion(name: str, conf: dict, baseline_agg: dict, current_agg: dict) -> dict:
    """Return {conclusion, metric, baseline, current, level} (level 0 = unchanged)."""
    path = conf["metric"]
    baseline = metric_path(baseline_agg, path)
    current = metric_path(current_agg, path)
    kind = conf.get("kind", "share")
    result = {
        "conclusion": name,
        "metric": path,
        "baseline": baseline,
        "current": current,
        "level": 0,
    }
    if baseline is None or current is None:
        result["level"] = 0
        result["note"] = "not comparable (missing value)"
        return result

    if kind == "share":
        pp = _pp_change(baseline, current)
        result["change_pp"] = pp
        threshold = conf.get("level1", {}).get("absolute_pp", 5)
        if pp is not None and abs(pp) >= threshold:
            result["level"] = 1
    elif kind == "numeric":
        result["change"] = round(current - baseline, 1)
        threshold = conf.get("level1", {}).get("absolute_change", 50)
        if abs(current - baseline) >= threshold:
            result["level"] = 1
        if result["level"] >= 1 and conf.get("level2") == "median_band_change":
            if _band_change(baseline_agg, current, baseline):
                result["level"] = 2
    elif kind == "categorical":
        if str(baseline) != str(current):
            result["level"] = 2
    return result


def compute_drift(
    baseline_aggregate: dict,
    current_metrics: dict,
    conclusions: Optional[dict] = None,
    conclusions_path: str = DEFAULT_CONCLUSIONS_PATH,
    previous_panel: Optional[dict] = None,
    roster_turnover_rate: Optional[float] = None,
    turnover_threshold: float = 0.15,
) -> DriftReport:
    """Compare baseline vs current; deterministic levels 0/1/2.

    Suppression rules (never auto Level 2 on the overall cohort):
    - tracked-team scope changed (scope_changed=True);
    - roster turnover >= turnover_threshold (cohort unstable).
    The matched panel is always computed independently.
    """
    if conclusions is None:
        conclusions = load_conclusions(conclusions_path)

    baseline_agg = baseline_aggregate["aggregate"] if "aggregate" in baseline_aggregate else baseline_aggregate
    current_agg = current_metrics["aggregate"]
    current_panel = current_metrics.get("panel", {})

    # ---- series compatibility --------------------------------------------
    # A baseline from a different cohort series (e.g. the legacy 2026-05
    # extended snapshot) must NOT be compared for headline Level 1/2.
    base_series = (baseline_agg.get("series") or {}).get("series_id")
    cur_series = (current_agg.get("series") or {}).get("series_id")
    series_compatible = bool(base_series and base_series == cur_series)
    baseline_incompatible_reason = ""
    if not series_compatible:
        baseline_incompatible_reason = (
            f"baseline series {base_series!r} != current series {cur_series!r}; "
            "baseline incompatible — the first accepted hltv-core-v2 snapshot "
            "will initialize the new longitudinal series"
        )

    # ---- tracked-team scope comparison --------------------------------
    base_scope = baseline_agg.get("scope") or {}
    cur_scope = current_agg.get("scope") or {}
    scope_changed = False
    scope_warning = ""
    if base_scope.get("scope_id") != cur_scope.get("scope_id") or \
            set(base_scope.get("tracked_teams") or []) != set(cur_scope.get("tracked_teams") or []):
        scope_changed = True
        scope_warning = (
            "tracked-team scope changed between baseline and current snapshot; "
            "overall cohort conclusion flips are NOT judged as Level 2 — "
            "scope change requires human review (matched-panel comparison only)"
        )

    # ---- roster stability ----------------------------------------------
    from .roster import roster_stability

    cohort_stability = roster_stability(roster_turnover_rate, turnover_threshold)
    headline_suppressed = False
    suppression_reason = ""
    if scope_changed:
        headline_suppressed = True
        suppression_reason = "tracked-team scope changed"
    elif cohort_stability == "unstable":
        headline_suppressed = True
        suppression_reason = f"high roster turnover (>= {turnover_threshold:.0%})"

    changed = [
        _evaluate_conclusion(name, conf, baseline_agg, current_agg)
        for name, conf in conclusions.items()
    ]
    changed = [c for c in changed if c["level"] > 0]
    if not series_compatible:
        # different cohort series: no headline Level 1/2 comparison at all
        for c in changed:
            c["level"] = 0
            c["note"] = "series incompatible; headline comparison disabled"
        changed = []
        level = 0
    elif headline_suppressed:
        # cap any conclusion-level change at Level 1 when the headline is
        # suppressed (scope changed or roster unstable)
        for c in changed:
            if c["level"] > 1:
                c["level"] = 1
                c["note"] = f"capped to Level 1: {suppression_reason}; human review required"
        level = max([c["level"] for c in changed], default=0)
    else:
        level = max([c["level"] for c in changed], default=0)

    baseline_panel = baseline_aggregate.get("panel") if isinstance(baseline_aggregate, dict) else None
    if baseline_panel is None:
        baseline_panel = {"status": "unavailable", "player_ids": []}

    baseline_ids = set(baseline_panel.get("player_ids", []))
    current_ids = set(current_panel.get("player_ids", []))

    cohort_change = {
        "baseline_players": len(baseline_ids),
        "current_players": len(current_ids),
        "added": sorted(current_ids - baseline_ids),
        "removed": sorted(baseline_ids - current_ids),
    }

    matched = sorted(baseline_ids & current_ids)
    matched_change: dict = {
        "status": "available" if (baseline_ids and matched) else "unavailable",
        "matched_count": len(matched),
        "baseline_count": len(baseline_ids),
        "current_count": len(current_ids),
    }
    if matched:
        # same-player settings change on the matched panel (work/ only data)
        base_panel = (previous_panel or {}).get("panel") if isinstance(previous_panel, dict) else previous_panel
        base_players = (base_panel or {}).get("players") or {}
        cur_players = current_panel.get("players") or {}
        if base_players and cur_players:
            per_field: dict[str, dict] = {}
            for fld in ("dpi", "edpi", "resolution", "polling_rate"):
                changed_count = sum(
                    1 for pid in matched
                    if pid in base_players and pid in cur_players
                    and base_players[pid].get(fld) != cur_players[pid].get(fld)
                )
                per_field[fld] = {"changed": changed_count, "compared": len(matched)}
            matched_change["per_field"] = per_field
        else:
            matched_change["per_field"] = None
            matched_change["note"] = "per-player baseline values unavailable"

    return DriftReport(
        level=level,
        changed_metrics=changed,
        cohort_change=cohort_change,
        matched_panel_change=matched_change,
        baseline_snapshot_date=baseline_agg.get("snapshot_date"),
        current_snapshot_date=current_agg.get("snapshot_date"),
        scope_changed=scope_changed,
        scope_warning=scope_warning,
        cohort_stability=cohort_stability,
        roster_turnover_rate=roster_turnover_rate,
        headline_suppressed=headline_suppressed,
        suppression_reason=suppression_reason,
        series_compatible=series_compatible,
        baseline_incompatible_reason=baseline_incompatible_reason,
    )
