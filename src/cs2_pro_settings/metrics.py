"""Deterministic aggregate metrics.

Output schema matches data/aggregate/2026-05.json so snapshots are comparable
across time.  Every share/count is accompanied by its valid_n; a missing field
never falls back to the full cohort size as denominator.

Determinism: category ordering is count-desc then key-asc; no dict-ordering
dependencies are left to chance.
"""
from __future__ import annotations

import statistics
from typing import Any, Optional

from .models import NormalizedPlayerSettings

# Real normalized settings attributes (excludes identity metadata:
# player_id / canonical_name / team / cohort_tier / provenance)
_SETTINGS_FIELDS = tuple(
    f.name for f in NormalizedPlayerSettings.__dataclass_fields__.values()
    if f.name not in ("player_id", "canonical_name", "team", "cohort_tier",
                      "provenance")
)

EDPI_BINS = [(0, 400, "0-400"), (400, 600, "400-600"), (600, 800, "600-800"),
             (800, 1000, "800-1000"), (1000, 1200, "1000-1200"), (1200, 1600, "1200-1600"),
             (1600, float("inf"), "1600+")]


def _counts(values: list[Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in values:
        if v is None:
            continue
        key = str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)
        out[key] = out.get(key, 0) + 1
    # deterministic ordering: count desc, key asc
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def _share(num: int, den: int) -> Optional[float]:
    return round(num / den, 4) if den else None


def _valid_n(values: list[Any]) -> int:
    return sum(1 for v in values if v is not None)


def _numeric_key(s: str) -> float:
    """Parse a category key like '600' to a number (non-numeric -> -1)."""
    try:
        return float(s)
    except (TypeError, ValueError):
        return -1.0


def _top(cats: dict[str, int]) -> Optional[str]:
    return next(iter(cats)) if cats else None


def compute_metrics(
    players: list[NormalizedPlayerSettings],
    snapshot_date: str,
    source_note: str = "",
    scope: Optional[dict] = None,
    series: Optional[dict] = None,
) -> dict:
    """Compute the aggregate snapshot schema from normalized players.

    players should already be filtered to the desired segment; the caller
    (CLI) computes core / core_plus_watchlist / all_tracked separately.
    series identifies the longitudinal series (e.g. vrs-core-v2); different
    series are NOT directly comparable for headline drift.
    """
    n = len(players)

    edpi = [p.edpi for p in players]
    edpi_valid = [v for v in edpi if v is not None]
    edpi_dist: dict[str, int] = {}
    for lo, hi, label in EDPI_BINS:
        edpi_dist[label] = sum(1 for v in edpi_valid if lo <= v < hi)

    dpi_cats = _counts([p.dpi for p in players])
    dpi_valid = _valid_n([p.dpi for p in players])

    res_cats = _counts([p.resolution for p in players])
    res_valid = _valid_n([p.resolution for p in players])

    aspect_cats = _counts([p.aspect_ratio for p in players])
    aspect_valid = _valid_n([p.aspect_ratio for p in players])

    rr_cats = _counts([p.refresh_rate for p in players])
    rr_valid = _valid_n([p.refresh_rate for p in players])

    fps_cats = _counts([p.max_fps for p in players])
    fps_valid = _valid_n([p.max_fps for p in players])

    both_off = sum(1 for p in players if p.crosshair_dot is False and p.crosshair_outline is False)
    ch_valid = sum(1 for p in players if p.crosshair_dot is not None and p.crosshair_outline is not None)

    color_cats = _counts([p.crosshair_color for p in players])
    color_valid = _valid_n([p.crosshair_color for p in players])

    fov = [p.viewmodel_fov for p in players]
    fov_valid = _valid_n(fov)
    fov68 = sum(1 for v in fov if v == 68)

    offsets = [p for p in players
               if p.viewmodel_offset_x is not None and p.viewmodel_offset_y is not None
               and p.viewmodel_offset_z is not None]
    dom_offset: Optional[tuple[float, float, float]] = None
    if offsets:
        combo_counts: dict[tuple[float, float, float], int] = {}
        for p in offsets:
            x, y, z = p.viewmodel_offset_x, p.viewmodel_offset_y, p.viewmodel_offset_z
            assert x is not None and y is not None and z is not None
            key = (x, y, z)
            combo_counts[key] = combo_counts.get(key, 0) + 1
        # deterministic tie-break: highest count, then lexicographically
        # smallest tuple (no insertion-order dependence)
        dom_offset = max(combo_counts, key=lambda k: (combo_counts[k], tuple(-v for v in k)))

    bri = [p.brightness for p in players]
    bri_cats = _counts(bri)
    bri_valid = _valid_n(bri)

    radar_rot = [p.radar_rotating for p in players]
    radar_cent = [p.radar_centered for p in players]
    # radar denominators are computed separately: rotating and centered are
    # independent fields with their own valid_n (they may differ)
    radar_rot_valid = _valid_n(radar_rot)
    radar_cent_valid = _valid_n(radar_cent)
    radar_rot_yes = sum(1 for v in radar_rot if v is True)
    radar_cent_yes = sum(1 for v in radar_cent if v is True)

    hz = [p.polling_rate for p in players]
    hz_cats = _counts(hz)
    hz_valid = _valid_n(hz)
    hz_4000_plus = sum(1 for v in hz if v is not None and v >= 4000)

    dpi_1600_plus = sum(1 for v in [p.dpi for p in players] if v is not None and v >= 1600)

    # SETTINGS AVAILABILITY: cohort membership (len(players)) is decided by
    # roster + inclusion policy + stable identity; field availability is
    # separate. players_with_any_setting counts cohort members with at
    # least one real normalized settings attribute (excludes identity
    # metadata: player_id/canonical_name/team/cohort_tier).
    any_setting = 0
    for p in players:
        if any(getattr(p, f) is not None for f in _SETTINGS_FIELDS):
            any_setting += 1
    settings_availability = {
        "cohort_players": n,
        "players_with_any_setting": any_setting,
        "players_with_zero_settings": n - any_setting,
        "any_setting_share": round(any_setting / n, 4) if n else None,
    }

    aggregate = {
        "snapshot_date": snapshot_date,
        "player_count": n,
        "team_count": len({p.team for p in players if p.team}),
        "settings_availability": settings_availability,
        "source": {"primary": source_note or "v2-pipeline"},
        "scope": scope or {"scope_id": None, "tracked_teams": [], "tracked_team_count": 0},
        "series": series or {"series_id": "unknown", "cohort_semantics": "unknown"},
        "edpi": {
            "count": len(edpi_valid),
            "median": round(statistics.median(edpi_valid), 1) if edpi_valid else None,
            "mean": round(sum(edpi_valid) / len(edpi_valid), 1) if edpi_valid else None,
            "distribution": edpi_dist,
        },
        "dpi": {
            "valid_n": dpi_valid,
            "categories": dpi_cats,
            "top_category": _top(dpi_cats),
            "share_800": _share(dpi_cats.get("800", 0), dpi_valid),
            "share_400": _share(dpi_cats.get("400", 0), dpi_valid),
            "share_1600_plus": _share(dpi_1600_plus, dpi_valid),
        },
        "resolution": {
            "valid_n": res_valid,
            "categories": res_cats,
            "top_category": _top(res_cats),
            "share_1280x960": _share(res_cats.get("1280x960", 0), res_valid),
        },
        "aspect_ratio": {
            "valid_n": aspect_valid,
            "categories": aspect_cats,
            "share_4_3": _share(aspect_cats.get("4:3", 0), aspect_valid),
        },
        "refresh_rate": {
            "valid_n": rr_valid,
            "categories": rr_cats,
            "share_360": _share(rr_cats.get("360", 0), rr_valid),
            "share_540_plus": _share(
                sum(count for k, count in rr_cats.items() if _numeric_key(k) >= 540),
                rr_valid,
            ),
        },
        "fps_max": {
            "valid_n": fps_valid,
            "categories": fps_cats,
            "unlimited_share": _share(fps_cats.get("0", 0), fps_valid),
        },
        "crosshair": {
            "valid_n": ch_valid,
            "dot_outline_off_share": _share(both_off, ch_valid),
            "color_categories": color_cats,
            "top_color": _top(color_cats),
        },
        "viewmodel": {
            "valid_n": fov_valid,
            "fov68_share": _share(fov68, fov_valid),
            "dominant_offset": list(dom_offset) if dom_offset else None,
        },
        "brightness": {
            "valid_n": bri_valid,
            "categories": bri_cats,
        },
        "radar": {
            # legacy-compatible alias: rotating valid_n (2026-05 schema)
            "valid_n": radar_rot_valid,
            "rotating_valid_n": radar_rot_valid,
            "centered_valid_n": radar_cent_valid,
            "rotating_share": _share(radar_rot_yes, radar_rot_valid),
            "centered_share": _share(radar_cent_yes, radar_cent_valid),
        },
        "mouse_polling": {
            "valid_n": hz_valid,
            "categories": hz_cats,
            "share_4000_plus": _share(hz_4000_plus, hz_valid),
        },
    }

    # panel metadata for matched-panel drift analysis (ids only in the public
    # snapshot; per-player values live in work/ only).
    panel = {
        "status": "available" if n else "empty",
        "player_ids": sorted(p.player_id for p in players),
        "players": {
            p.player_id: {
                "dpi": p.dpi,
                "edpi": p.edpi,
                "resolution": p.resolution,
                "polling_rate": p.polling_rate,
            }
            for p in players
        },
    }

    return {"aggregate": aggregate, "panel": panel}


def public_aggregate(metrics: dict) -> dict:
    """Public snapshot shape: aggregates + panel METADATA only.

    Per-player values and stable identity lists (SteamIDs) are operational
    state, NOT public data. The public panel carries status and counts so
    downstream consumers can reason about matched-panel availability without
    a row-equivalent identity list.
    """
    agg = dict(metrics["aggregate"])
    panel = metrics.get("panel", {})
    ids = panel.get("player_ids") or []
    return {
        "aggregate": agg,
        "panel": {
            "status": panel.get("status", "unavailable" if not ids else "available"),
            "player_count": len(ids),
            "stable_identity_count": len(ids),
        },
    }


def metric_path(aggregate: dict, dotted: str) -> Any:
    cur: Any = aggregate
    for part in dotted.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur
