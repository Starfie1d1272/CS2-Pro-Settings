"""Deterministic aggregate metrics.

The schema remains backward-compatible with data/aggregate/2026-05.json and
adds field-specific reporting blocks over time. Every share/count is paired
with its valid_n; a missing field never falls back to the full cohort size as
denominator.

Determinism: category ordering is count-desc then key-asc; no dict-ordering
dependencies are left to chance.
"""
from __future__ import annotations

from collections import Counter
import statistics
from typing import Any, Optional

from .models import CUSTOM_COLOR_CODE, NormalizedPlayerSettings

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

# eDPI is usually source-provided alongside DPI and sensitivity.  Treat it as
# arithmetically inconsistent only when the difference exceeds BOTH ordinary
# rounding noise (2 eDPI) and 1% of the calculated value.  This is a QC flag,
# not a replacement rule: the reconciled source value remains unchanged.
EDPI_QC_ABS_TOLERANCE = 2.0
EDPI_QC_REL_TOLERANCE = 0.01


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


def _categorical_block(values: list[Any]) -> dict:
    """Additive aggregate block for a categorical field."""
    cats = _counts(values)
    return {
        "valid_n": _valid_n(values),
        "categories": cats,
        "top_category": _top(cats),
    }


def _numeric_block(values: list[Optional[float]]) -> dict:
    """Additive aggregate block for source-provided numeric values."""
    valid = [v for v in values if v is not None]
    cats = _counts(values)
    return {
        "valid_n": len(valid),
        "categories": cats,
        "median": round(statistics.median(valid), 4) if valid else None,
        "top_category": _top(cats),
    }


def _boolean_block(values: list[Optional[bool]], cohort_n: int) -> dict:
    """Known/unknown-aware summary; missing never enters the share."""
    valid_n = _valid_n(values)
    enabled = sum(1 for value in values if value is True)
    disabled = sum(1 for value in values if value is False)
    return {
        "valid_n": valid_n,
        "missing_n": cohort_n - valid_n,
        "enabled_count": enabled,
        "disabled_count": disabled,
        "enabled_share": _share(enabled, valid_n),
    }


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

    edpi_comparable = [
        p for p in players
        if p.dpi is not None and p.sensitivity is not None and p.edpi is not None
    ]
    edpi_anomalies = 0
    for p in edpi_comparable:
        assert p.dpi is not None and p.sensitivity is not None and p.edpi is not None
        calculated = p.dpi * p.sensitivity
        tolerance = max(EDPI_QC_ABS_TOLERANCE,
                        abs(calculated) * EDPI_QC_REL_TOLERANCE)
        if abs(p.edpi - calculated) > tolerance:
            edpi_anomalies += 1
    edpi_qc = {
        "comparable_n": len(edpi_comparable),
        "consistent_n": len(edpi_comparable) - edpi_anomalies,
        "anomaly_count": edpi_anomalies,
        "anomaly_share": _share(edpi_anomalies, len(edpi_comparable)),
        "missing_inputs_n": n - len(edpi_comparable),
        "absolute_tolerance": EDPI_QC_ABS_TOLERANCE,
        "relative_tolerance": EDPI_QC_REL_TOLERANCE,
    }

    dpi_cats = _counts([p.dpi for p in players])
    dpi_valid = _valid_n([p.dpi for p in players])

    res_cats = _counts([p.resolution for p in players])
    res_valid = _valid_n([p.resolution for p in players])

    aspect_cats = _counts([p.aspect_ratio for p in players])
    aspect_valid = _valid_n([p.aspect_ratio for p in players])

    scaling_mode = _categorical_block([p.scaling_mode for p in players])
    zoom_sensitivity = _numeric_block([p.zoom_sensitivity for p in players])
    boost_player = _boolean_block([p.boost_player for p in players], n)

    rr_cats = _counts([p.refresh_rate for p in players])
    rr_valid = _valid_n([p.refresh_rate for p in players])

    fps_cats = _counts([p.max_fps for p in players])
    fps_valid = _valid_n([p.max_fps for p in players])

    both_off = sum(1 for p in players if p.crosshair_dot is False and p.crosshair_outline is False)
    ch_valid = sum(1 for p in players if p.crosshair_dot is not None and p.crosshair_outline is not None)

    color_cats = _counts([p.crosshair_color for p in players])
    color_valid = _valid_n([p.crosshair_color for p in players])

    crosshair_geometry = {
        "style": _categorical_block([p.crosshair_style for p in players]),
        "size": _numeric_block([p.crosshair_size for p in players]),
        "gap": _numeric_block([p.crosshair_gap for p in players]),
        "thickness": _numeric_block([p.crosshair_thickness for p in players]),
        "alpha": _numeric_block([p.crosshair_alpha for p in players]),
        "dot": _boolean_block([p.crosshair_dot for p in players], n),
        "outline": _boolean_block([p.crosshair_outline for p in players], n),
    }

    # Figure-only joint counts.  The public aggregate intentionally keeps the
    # backward-compatible marginal geometry blocks above; this identity-free
    # work-state block lets production figures show the observed Gap x Size
    # structure without reconstructing a false joint distribution from those
    # marginals.  public_aggregate() does not expose figure_data.
    gap_size_counts = Counter(
        (p.crosshair_gap, p.crosshair_size)
        for p in players
        if p.crosshair_gap is not None and p.crosshair_size is not None
    )
    crosshair_gap_size = {
        "valid_n": sum(gap_size_counts.values()),
        "combinations": [
            {"gap": gap, "size": size, "count": count}
            for (gap, size), count in sorted(
                gap_size_counts.items(),
                key=lambda item: (-item[1], item[0][0], item[0][1]),
            )
        ],
    }

    # Custom RGB: interpreted ONLY when the raw crosshair mode code is the
    # game's custom-RGB value (cl_crosshaircolor 5, CUSTOM_COLOR_CODE) AND
    # the R/G/B channels are all present. Preset-mode RGB is latent/
    # inactive state (see models.py) and never enters this denominator;
    # a missing channel makes the player Custom-RGB-missing, never
    # defaulted to 255,255,255. The mode code is the authoritative switch.
    custom_players = sum(1 for p in players
                         if p.crosshair_color_code == CUSTOM_COLOR_CODE)
    rgb_keys = [
        f"{p.crosshair_color_r},{p.crosshair_color_g},{p.crosshair_color_b}"
        for p in players
        if p.crosshair_color_code == CUSTOM_COLOR_CODE
        and p.crosshair_color_r is not None
        and p.crosshair_color_g is not None
        and p.crosshair_color_b is not None
    ]
    rgb_cats = _counts(rgb_keys)
    rgb_valid = len(rgb_keys)
    top_rgb = _top(rgb_cats)
    custom_rgb = {
        "valid_n": rgb_valid,
        "custom_players": custom_players,
        "coverage": _share(rgb_valid, custom_players),
        "categories": rgb_cats,
        "unique_colors": len(rgb_cats),
        "top_rgb": top_rgb,
        "top_rgb_share": _share(rgb_cats.get(top_rgb, 0), rgb_valid) if top_rgb else None,
    }

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
            "consistency_qc": edpi_qc,
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
        "scaling_mode": scaling_mode,
        "zoom_sensitivity": zoom_sensitivity,
        "boost_player": boost_player,
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
            "color_valid_n": color_valid,
            "color_categories": color_cats,
            "top_color": _top(color_cats),
            "custom_rgb": custom_rgb,
            "geometry": crosshair_geometry,
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
            "zoom": _numeric_block([p.radar_zoom for p in players]),
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

    return {
        "aggregate": aggregate,
        "panel": panel,
        "figure_data": {"crosshair_gap_size": crosshair_gap_size},
    }


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
