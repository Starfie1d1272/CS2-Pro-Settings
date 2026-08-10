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
) -> DriftReport:
    """Compare baseline vs current; deterministic levels 0/1/2."""
    if conclusions is None:
        conclusions = load_conclusions(conclusions_path)

    baseline_agg = baseline_aggregate["aggregate"] if "aggregate" in baseline_aggregate else baseline_aggregate
    current_agg = current_metrics["aggregate"]
    current_panel = current_metrics.get("panel", {})

    changed = [
        _evaluate_conclusion(name, conf, baseline_agg, current_agg)
        for name, conf in conclusions.items()
    ]
    changed = [c for c in changed if c["level"] > 0]
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
        base_players = (previous_panel or {}).get("players") or {}
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
    )
