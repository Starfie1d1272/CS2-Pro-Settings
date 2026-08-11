"""Deterministic bilingual snapshot report generation (data-first).

Reports answer "what settings do the pros use this month?" — not
methodology. Architecture (shared logic -> locale wording):

    metrics / drift / manifest / source status / conflicts
                        |
                        v
              build_report_view()   <- ALL numbers, valid_n, availability
                                       branches, section visibility,
                                       first-baseline judgment
                        |
            +-----------+-----------+
            v                       v
      _render_en(view)         _render_zh(view)
      (locale wording only)    (locale wording only)

Section visibility is decided ONCE in the view model and is identical in
both languages:

- no data -> no section (refresh/fps/radar-rotating with valid_n=0 are
  omitted entirely)
- conflict_count == 0 -> no conflict section
- no real extended-segment values -> no segments section
- first same-series snapshot -> no longitudinal comparison section (only a
  "baseline" marker in the top metadata line)

No LLM is used; interpretation sentences are fixed factual statements
derived from the shared numbers, and basic-statistics concepts are never
explained.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# shared field registry (single source of truth for the coverage table)
# ---------------------------------------------------------------------------

FIELD_KEYS = [
    "edpi", "dpi", "resolution", "aspect_ratio", "crosshair", "viewmodel",
    "polling", "refresh", "fps", "radar_centered", "radar_rotating",
]

FIELD_LABELS_EN = {
    "edpi": "eDPI", "dpi": "DPI", "resolution": "Resolution",
    "aspect_ratio": "Aspect ratio", "crosshair": "Crosshair",
    "viewmodel": "Viewmodel FOV", "polling": "Mouse polling rate",
    "refresh": "Monitor refresh rate", "fps": "fps_max",
    "radar_centered": "Radar centered", "radar_rotating": "Radar rotating",
}

FIELD_LABELS_ZH = {
    "edpi": "eDPI", "dpi": "DPI", "resolution": "分辨率",
    "aspect_ratio": "宽高比", "crosshair": "准星",
    "viewmodel": "Viewmodel FOV", "polling": "鼠标回报率",
    "refresh": "显示器刷新率", "fps": "fps_max",
    "radar_centered": "Radar centered", "radar_rotating": "Radar rotating",
}

# logical figure name -> real file under figures/<scope>/
FIGURE_FILES = {
    "edpi": "edpi.png",
    "dpi": "dpi.png",
    "polling": "polling_rate.png",
    "aspect_ratio": "aspect_ratio.png",
    "resolution": "resolution.png",
    "crosshair": "crosshair_color.png",
    "viewmodel": "fov.png",
}

# ---------------------------------------------------------------------------
# formatting helpers
# ---------------------------------------------------------------------------


def _pct(v: Optional[float]) -> str:
    return f"{v * 100:.1f}%" if v is not None else "n/a"


def _num(v: Optional[float]) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return f"{v:g}"


def _as_int(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _dg(drift: Any, key: str, default=None):
    if isinstance(drift, dict):
        return drift.get(key, default)
    return getattr(drift, key, default)


def _dominant_range(dist: dict, median: Optional[float]) -> Optional[tuple[str, int, int]]:
    """Narrowest contiguous distribution range holding a majority.

    Deterministic rule: start from the bin containing the median and expand
    toward the larger neighbour until the cumulative count is >= 50% of the
    total. Returns (range_label, count, total) or None when not computable.
    """
    if not dist or median is None:
        return None
    total = sum(dist.values())
    if total <= 0:
        return None
    ordered = [
        ("0-400", 0, 400), ("400-600", 400, 600), ("600-800", 600, 800),
        ("800-1000", 800, 1000), ("1000-1200", 1000, 1200),
        ("1200-1600", 1200, 1600), ("1600+", 1600, float("inf")),
    ]
    idx = None
    for i, (label, lo, hi) in enumerate(ordered):
        if label not in dist:
            continue
        if lo <= median < hi:
            idx = i
            break
    if idx is None:
        idx = max(range(len(ordered)), key=lambda i: dist.get(ordered[i][0], 0))
    chosen = [idx]
    count = dist.get(ordered[idx][0], 0)
    while count * 2 < total:
        cand = []
        for i in (idx - 1, idx + 1):
            if 0 <= i < len(ordered) and i not in chosen:
                cand.append((i, dist.get(ordered[i][0], 0)))
        if not cand:
            break
        nxt, _n = max(cand, key=lambda ic: ic[1])
        chosen.append(nxt)
        count += dist.get(ordered[nxt][0], 0)
    chosen = sorted(chosen)
    if chosen[0] == chosen[-1]:
        label = ordered[chosen[0]][0]
    else:
        lo_val = ordered[chosen[0]][1]
        hi_val = ordered[chosen[-1]][2]
        if hi_val == float("inf"):
            label = f"{lo_val:g}+"
        else:
            label = f"{lo_val:g}–{hi_val:g}"
    return label, count, total


def _cats_pct(cats: dict, keys) -> str:
    """Percentage from RAW category counts (no rounded-share float edges)."""
    total = sum(cats.values())
    if total <= 0:
        return "n/a"
    num = sum(cats.get(k, 0) for k in keys)
    return f"{num / total * 100:.1f}%"


def _cats_ge_pct(cats: dict, min_value: float) -> str:
    total = sum(cats.values())
    if total <= 0:
        return "n/a"
    num = 0
    for k, v in cats.items():
        try:
            if float(k) >= min_value:
                num += v
        except (TypeError, ValueError):
            continue
    return f"{num / total * 100:.1f}%"


def _cats_share_num(cats: dict, key: str) -> Optional[int]:
    """Raw count of one category key, or None when categories are empty."""
    if not cats:
        return None
    return cats.get(key, 0)


def _cats_top_rows(cats: dict, limit: int = 6) -> list[tuple[str, int, int]]:
    """Deterministic category ranking: (category, count, total), count-desc.

    This is the SINGLE source of truth for "top category / runner-up"
    rendering: renderers never assume a specific category (4:3, 1280x960,
    16:9, 1920x1080, ...) is first or second.
    """
    total = sum(cats.values())
    if total <= 0:
        return []
    ordered = sorted(cats.items(), key=lambda kv: (-kv[1], kv[0]))
    return [(k, v, total) for k, v in ordered[:limit]]


def _cats_combined_share(cats: dict, keys) -> Optional[tuple[int, int]]:
    """(combined_count, total) for a fixed set of category keys (raw)."""
    total = sum(cats.values())
    if total <= 0:
        return None
    return (sum(cats.get(k, 0) for k in keys), total)


def _numeric_key(s: str) -> float:
    try:
        return float(s)
    except (TypeError, ValueError):
        return -1.0


def _offset_text(offset: Any) -> str:
    if not offset:
        return "n/a"
    try:
        parts = [f"{v:g}" for v in offset]
    except TypeError:
        return str(offset)
    labels = ("X", "Y", "Z")
    return ", ".join(f"{n}={v}" for n, v in zip(labels, parts))


_PROVIDER_LABELS = {"valve": "Valve VRS", "hltv": "HLTV"}

# ---------------------------------------------------------------------------
# report view model (ALL shared logic lives here)
# ---------------------------------------------------------------------------


@dataclass
class ReportView:
    locale: str = "en"

    # top metadata
    snapshot_month: str = "n/a"
    snapshot_date: str = "n/a"
    series_id: str = "n/a"
    core_snapshot_date: str = "n/a"
    team_count: str = "n/a"
    player_count: str = "n/a"
    players_with_any_setting: str = "n/a"
    any_setting_pct: str = "n/a"
    players_with_zero_settings: str = "n/a"
    first_snapshot: bool = True

    # key numbers / metrics (None-valued -> row omitted)
    edpi_median: str = "n/a"
    edpi_mean: str = "n/a"
    edpi_n: int = 0
    edpi_core_label: str = ""
    edpi_core_count: int = 0
    edpi_core_total: int = 0
    dpi_top_category: str = "n/a"
    dpi_400_pct: str = "n/a"
    dpi_800_pct: str = "n/a"
    dpi_1600_plus_pct: str = "n/a"
    dpi_400_count: Optional[int] = None
    dpi_800_count: Optional[int] = None
    dpi_n: int = 0
    polling_1000_pct: str = "n/a"
    polling_2000_pct: str = "n/a"
    polling_4000_pct: str = "n/a"
    polling_8000_pct: str = "n/a"
    polling_4000_plus_pct: str = "n/a"
    polling_4000_plus_count: Optional[int] = None
    polling_n: int = 0
    # dynamic category rankings (top / runner-up, never hard-coded labels)
    aspect_rank: list[tuple[str, int, int]] = field(default_factory=list)
    aspect_n: int = 0
    resolution_rank: list[tuple[str, int, int]] = field(default_factory=list)
    resolution_n: int = 0
    crosshair_minimal_pct: str = "n/a"
    crosshair_n: int = 0
    crosshair_color_rows: list[tuple[str, int, int]] = field(default_factory=list)
    fov68_pct: str = "n/a"
    viewmodel_dominant_offset: str = "n/a"
    fov_n: int = 0
    radar_centered_available: bool = False
    radar_centered_pct: str = "n/a"
    radar_centered_n: int = 0

    # longitudinal (only when a same-series previous snapshot exists)
    previous_snapshot: str = "n/a"
    previous_player_count: str = "n/a"
    roster_turnover: str = "unavailable"
    matched_count: str = "unavailable"
    longitudinal_changes: list[str] = field(default_factory=list)
    matched_panel_summary: list[str] = field(default_factory=list)

    # extended segments (real values only; empty -> section omitted)
    segment_rows: list[dict] = field(default_factory=list)

    # data coverage
    field_rows: list[tuple[str, int, int]] = field(default_factory=list)

    # sources / conflicts
    source_lines: list[str] = field(default_factory=list)
    conflict_count: int = 0

    # data & code
    data_link: str = "n/a"
    figure_scope: str = "latest"


def _field_rows(agg: dict, player_count: int) -> list[tuple[str, int, int]]:
    rows: list[tuple[str, int, int]] = []
    edpi = agg.get("edpi") or {}
    edpi_count = edpi.get("count") if edpi.get("count") is not None else (edpi.get("valid_n") or 0)
    rows.append(("edpi", _as_int(edpi_count), player_count))
    rows.append(("dpi", _as_int((agg.get("dpi") or {}).get("valid_n")), player_count))
    rows.append(("resolution", _as_int((agg.get("resolution") or {}).get("valid_n")), player_count))
    rows.append(("aspect_ratio", _as_int((agg.get("aspect_ratio") or {}).get("valid_n")), player_count))
    rows.append(("crosshair", _as_int((agg.get("crosshair") or {}).get("valid_n")), player_count))
    rows.append(("viewmodel", _as_int((agg.get("viewmodel") or {}).get("valid_n")), player_count))
    rows.append(("polling", _as_int((agg.get("mouse_polling") or {}).get("valid_n")), player_count))
    rows.append(("refresh", _as_int((agg.get("refresh_rate") or {}).get("valid_n")), player_count))
    rows.append(("fps", _as_int((agg.get("fps_max") or {}).get("valid_n")), player_count))
    radar = agg.get("radar") or {}
    rows.append(("radar_centered", _as_int(radar.get("centered_valid_n", radar.get("valid_n"))), player_count))
    rows.append(("radar_rotating", _as_int(radar.get("rotating_valid_n", radar.get("valid_n"))), player_count))
    return rows


def _segment_rows(metrics: dict) -> list[dict]:
    """Non-Core extended segments with REAL values only.

    A segment row is emitted only when it has actual player counts / medians.
    The VRS Core row is not repeated (it IS the headline cohort). If no
    non-Core segment has real values, the whole section is omitted.
    """
    segments = metrics.get("segments") or {}
    if not segments:
        return []
    rows: list[dict] = []
    order = ("consensus", "ranked_union", "core_plus_watchlist", "all_tracked")
    for key in order:
        seg = segments.get(key) or {}
        pc = seg.get("player_count")
        tc = seg.get("team_count")
        med = (seg.get("edpi") or {}).get("median") if seg.get("edpi") else None
        if not pc or not tc or med is None:
            continue
        rows.append({
            "key": key,
            "teams": str(tc),
            "players": str(pc),
            "edpi": _num(med),
        })
    return rows


def build_report_view(
    metrics: dict,
    drift: Any,
    source_status: dict,
    conflicts: list[dict],
    baseline: Optional[dict] = None,
    roster_report: Optional[dict] = None,
    manifest: Optional[dict] = None,
    legacy_snapshot: Optional[dict] = None,
    figure_scope: str = "latest",
    locale: str = "en",
) -> ReportView:
    """Compute the complete report view (numbers + section visibility).

    All denominators, availability branches and the first-baseline judgment
    are computed HERE once; locale renderers only translate wording.
    """
    agg = metrics.get("aggregate", {}) if isinstance(metrics, dict) else {}
    panel = metrics.get("panel", {}) if isinstance(metrics, dict) else {}
    scope = agg.get("scope") or {}
    series = agg.get("series") or {}
    av = agg.get("settings_availability") or {}

    player_count = agg.get("player_count") or 0
    team_count = agg.get("team_count")
    snapshot_date = agg.get("snapshot_date") or "n/a"
    snapshot_month = snapshot_date[:7] if isinstance(snapshot_date, str) else "n/a"

    v = ReportView(locale=locale, figure_scope=figure_scope)
    v.snapshot_month = snapshot_month
    v.snapshot_date = snapshot_date
    v.series_id = series.get("series_id", "n/a")
    v.core_snapshot_date = str(scope.get("core_snapshot") or "n/a")
    v.team_count = str(team_count) if team_count is not None else "n/a"
    v.player_count = str(player_count) if player_count else "n/a"

    n = av.get("cohort_players")
    m = av.get("players_with_any_setting")
    z = av.get("players_with_zero_settings")
    share = av.get("any_setting_share")
    v.players_with_any_setting = (f"{m}/{n}" if m is not None and n is not None else "n/a")
    v.any_setting_pct = _pct(share if isinstance(share, (int, float)) else None)
    v.players_with_zero_settings = str(z) if z is not None else "n/a"

    # ---- first-baseline judgment (drives section-7 visibility) ----------
    base_series = None
    if isinstance(baseline, dict):
        base_agg = baseline.get("aggregate", baseline)
        base_series = (base_agg.get("series") or {}).get("series_id")
    cur_series = series.get("series_id")
    series_compatible = bool(base_series and base_series == cur_series)
    baseline_date = _dg(drift, "baseline_snapshot_date")
    v.first_snapshot = bool(
        baseline is None or drift is None
        or not series_compatible
        or (baseline_date is not None and baseline_date == snapshot_date)
    )

    # ---- metrics ---------------------------------------------------------
    edpi = agg.get("edpi") or {}
    v.edpi_n = _as_int(edpi.get("count") if edpi.get("count") is not None else (edpi.get("valid_n") or 0))
    v.edpi_median = _num(edpi.get("median"))
    v.edpi_mean = _num(edpi.get("mean"))
    if v.edpi_n:
        rng = _dominant_range(edpi.get("distribution") or {}, edpi.get("median"))
        if rng:
            v.edpi_core_label, v.edpi_core_count, v.edpi_core_total = rng

    dpi = agg.get("dpi") or {}
    v.dpi_n = _as_int(dpi.get("valid_n"))
    v.dpi_top_category = str(dpi.get("top_category") or "n/a")
    dpi_cats = dpi.get("categories") or {}
    v.dpi_400_pct = _cats_pct(dpi_cats, ["400"])
    v.dpi_800_pct = _cats_pct(dpi_cats, ["800"])
    v.dpi_1600_plus_pct = _cats_ge_pct(dpi_cats, 1600) if dpi_cats else _pct(dpi.get("share_1600_plus"))
    v.dpi_400_count = _cats_share_num(dpi_cats, "400")
    v.dpi_800_count = _cats_share_num(dpi_cats, "800")

    poll = agg.get("mouse_polling") or {}
    v.polling_n = _as_int(poll.get("valid_n"))
    pcats = poll.get("categories") or {}
    v.polling_1000_pct = _cats_pct(pcats, ["1000"])
    v.polling_2000_pct = _cats_pct(pcats, ["2000"])
    v.polling_4000_pct = _cats_pct(pcats, ["4000"])
    v.polling_8000_pct = _cats_pct(pcats, ["8000"])
    v.polling_4000_plus_pct = _cats_ge_pct(pcats, 4000) if pcats else _pct(poll.get("share_4000_plus"))
    if pcats:
        v.polling_4000_plus_count = sum(c for k, c in pcats.items() if _numeric_key(k) >= 4000)

    aspect = agg.get("aspect_ratio") or {}
    v.aspect_n = _as_int(aspect.get("valid_n"))
    v.aspect_rank = _cats_top_rows(aspect.get("categories") or {})

    res = agg.get("resolution") or {}
    v.resolution_n = _as_int(res.get("valid_n"))
    v.resolution_rank = _cats_top_rows(res.get("categories") or {})

    ch = agg.get("crosshair") or {}
    v.crosshair_n = _as_int(ch.get("valid_n"))
    v.crosshair_minimal_pct = _pct(ch.get("dot_outline_off_share"))
    v.crosshair_color_rows = _cats_top_rows(ch.get("color_categories") or {})

    vm = agg.get("viewmodel") or {}
    v.fov_n = _as_int(vm.get("valid_n"))
    v.fov68_pct = _pct(vm.get("fov68_share"))
    v.viewmodel_dominant_offset = _offset_text(vm.get("dominant_offset"))

    radar = agg.get("radar") or {}
    v.radar_centered_n = _as_int(radar.get("centered_valid_n", radar.get("valid_n")))
    v.radar_centered_available = v.radar_centered_n > 0
    v.radar_centered_pct = _pct(radar.get("centered_share"))

    # ---- longitudinal (only rendered when NOT the first snapshot) -------
    v.previous_snapshot = str(baseline_date) if baseline_date else "n/a"
    cc = _dg(drift, "cohort_change") or {}
    v.previous_player_count = str(cc.get("baseline_players", "n/a"))
    turnover = _dg(drift, "roster_turnover_rate")
    if turnover is None and isinstance(roster_report, dict):
        turnover = roster_report.get("core_turnover_rate", roster_report.get("turnover_rate"))
    v.roster_turnover = _pct(turnover) if turnover is not None else "unavailable"
    mp = _dg(drift, "matched_panel_change") or {}
    v.matched_count = str(mp.get("matched_count", "unavailable")) if mp.get("matched_count") is not None else "unavailable"

    for c in _dg(drift, "changed_metrics") or []:
        if c.get("change_pp") is not None:
            delta = f"{c['change_pp']:+.1f}pp"
        elif c.get("change") is not None:
            delta = f"{c['change']:+.1f}"
        else:
            delta = "changed"
        v.longitudinal_changes.append(
            f"{c['conclusion']}: {c.get('baseline')} -> {c.get('current')} ({delta}) [level {c.get('level')}]")
    if mp.get("per_field"):
        for fld, info in mp["per_field"].items():
            parts = [f"{info.get('changed', 0)}/{info.get('compared', 0)} changed"]
            if info.get("missing_to_value"):
                parts.append(f"{info['missing_to_value']} missing->value")
            if info.get("value_to_missing"):
                parts.append(f"{info['value_to_missing']} value->missing")
            v.matched_panel_summary.append(f"{fld}: {', '.join(parts)}")

    # ---- extended segments (real values only) ---------------------------
    v.segment_rows = _segment_rows(metrics)

    # ---- data coverage ---------------------------------------------------
    v.field_rows = _field_rows(agg, player_count)

    # ---- sources / conflicts --------------------------------------------
    for name in sorted(source_status or {}):
        st = source_status[name]
        v.source_lines.append(name if str(st).startswith("ok") else f"{name}: {st}")
    v.conflict_count = len(conflicts) if isinstance(conflicts, list) else 0

    v.data_link = f"data/aggregate/{snapshot_month}.json" if snapshot_month != "n/a" else "data/aggregate/latest.json"
    return v


def read_legacy_metadata(data_agg_dir: Path, current_series_id: Optional[str]) -> Optional[dict]:
    """Find a dated aggregate from a DIFFERENT series (e.g. the 2026-05
    legacy snapshot) to describe the historical reference.

    Returns {snapshot_date, series_id, cohort_semantics} or None.
    """
    if not data_agg_dir.is_dir():
        return None
    best: Optional[dict] = None
    for p in sorted(data_agg_dir.glob("*.json")):
        if p.name == "latest.json":
            continue
        try:
            d = json_loads_safe(p)
        except Exception:
            continue
        agg = d.get("aggregate", d) if isinstance(d, dict) else {}
        sid = (agg.get("series") or {}).get("series_id")
        if sid and sid != current_series_id:
            best = {
                "snapshot_date": agg.get("snapshot_date"),
                "series_id": sid,
                "cohort_semantics": (agg.get("series") or {}).get("cohort_semantics"),
            }
    return best


def json_loads_safe(p: Path) -> dict:
    import json
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# locale renderers (wording only; numbers/visibility come from the view)
# ---------------------------------------------------------------------------


def _figure(view: ReportView, key: str) -> str:
    return f"![{FIGURE_FILES[key]}](../figures/{view.figure_scope}/{FIGURE_FILES[key]})"


def _key_numbers_en(v: ReportView) -> list[str]:
    rows = []
    if v.edpi_n:
        rows.append(f"- Median eDPI: **{v.edpi_median}** (n={v.edpi_n})")
    if v.dpi_n:
        rows.append(f"- DPI: 800 at {v.dpi_800_pct} · 400 at {v.dpi_400_pct} (n={v.dpi_n})")
    if v.aspect_rank:
        top, _c, _t = v.aspect_rank[0]
        rows.append(f"- {top}: **{_cats_pct_from_row(v.aspect_rank[0])}** (n={v.aspect_n})")
    if v.resolution_rank:
        top, _c, _t = v.resolution_rank[0]
        rows.append(f"- {top}: **{_cats_pct_from_row(v.resolution_rank[0])}** (n={v.resolution_n})")
    if v.polling_n:
        rows.append(f"- Polling: 1000 Hz at {v.polling_1000_pct} · 4000 Hz+ at {v.polling_4000_plus_pct} (n={v.polling_n})")
    if v.crosshair_n and v.crosshair_color_rows:
        top_color, _c, _t = v.crosshair_color_rows[0]
        rows.append(f"- Crosshair: minimal at {v.crosshair_minimal_pct} · top color category {top_color} at {_cats_pct_from_row(v.crosshair_color_rows[0])} (n={v.crosshair_n})")
    if v.fov_n:
        rows.append(f"- `viewmodel_fov 68`: **{v.fov68_pct}** (n={v.fov_n})")
    if v.radar_centered_available:
        rows.append(f"- Radar centered: {v.radar_centered_pct} (n={v.radar_centered_n})")
    return rows


def _key_numbers_zh(v: ReportView) -> list[str]:
    rows = []
    if v.edpi_n:
        rows.append(f"- 中位 eDPI：**{v.edpi_median}**（n={v.edpi_n}）")
    if v.dpi_n:
        rows.append(f"- DPI：800 占 {v.dpi_800_pct} · 400 占 {v.dpi_400_pct}（n={v.dpi_n}）")
    if v.aspect_rank:
        top, _c, _t = v.aspect_rank[0]
        rows.append(f"- {top}：**{_cats_pct_from_row(v.aspect_rank[0])}**（n={v.aspect_n}）")
    if v.resolution_rank:
        top, _c, _t = v.resolution_rank[0]
        rows.append(f"- {top}：**{_cats_pct_from_row(v.resolution_rank[0])}**（n={v.resolution_n}）")
    if v.polling_n:
        rows.append(f"- 回报率：1000 Hz 占 {v.polling_1000_pct} · 4000 Hz+ 占 {v.polling_4000_plus_pct}（n={v.polling_n}）")
    if v.crosshair_n and v.crosshair_color_rows:
        top_color, _c, _t = v.crosshair_color_rows[0]
        rows.append(f"- 准星：极简占 {v.crosshair_minimal_pct} · 颜色类别 {top_color} 占 {_cats_pct_from_row(v.crosshair_color_rows[0])}（n={v.crosshair_n}）")
    if v.fov_n:
        rows.append(f"- `viewmodel_fov 68`：**{v.fov68_pct}**（n={v.fov_n}）")
    if v.radar_centered_available:
        rows.append(f"- Radar centered：开启 {v.radar_centered_pct}（n={v.radar_centered_n}）")
    return rows


def _cats_pct_from_row(row: tuple[str, int, int]) -> str:
    _k, c, t = row
    return f"{c / t * 100:.1f}%" if t else "n/a"


def _render_en(v: ReportView, cross_link_base: str = "latest") -> str:
    fig = lambda k: _figure(v, k)  # noqa: E731
    sec = 0

    def heading(title: str) -> str:
        nonlocal sec
        sec += 1
        return f"## {sec}. {title}"

    lines: list[str] = []
    lines.append(f"# CS2 Professional Settings Snapshot — {v.snapshot_month}")
    lines.append("")
    lines.append(f"[中文版](./{cross_link_base}.zh-CN.md)")
    lines.append("")
    # compact metadata line
    meta = f"{v.snapshot_date} · VRS Top 30 ({v.core_snapshot_date}) · {v.team_count} teams · {v.player_count} players · {v.players_with_any_setting} settings"
    if v.first_snapshot:
        meta += f" · `{v.series_id}` baseline"
    else:
        meta += f" · `{v.series_id}`"
    lines.append(meta)
    lines.append("")

    # 1. key numbers
    key_rows = _key_numbers_en(v)
    if key_rows:
        lines.append(heading("Key numbers"))
        lines.append("")
        lines.extend(key_rows)
        lines.append("")

    # 2. mouse & sensitivity
    if v.edpi_n or v.dpi_n or v.polling_n:
        lines.append(heading("Mouse & sensitivity"))
        lines.append("")
        if v.edpi_n:
            lines.append("### eDPI")
            lines.append("")
            lines.append(fig("edpi"))
            lines.append("")
            lines.append(f"- Median: **{v.edpi_median}** · Mean: **{v.edpi_mean}** · n={v.edpi_n}")
            if v.edpi_core_label:
                lines.append(f"- {v.edpi_core_label} eDPI covers {v.edpi_core_count / v.edpi_core_total * 100:.1f}% of valid observations ({v.edpi_core_count}/{v.edpi_core_total}).")
            lines.append("")
        if v.dpi_n:
            lines.append("### DPI")
            lines.append("")
            lines.append(fig("dpi"))
            lines.append("")
            lines.append(f"- 800: **{v.dpi_800_pct}** · 400: {v.dpi_400_pct} · 1600+: {v.dpi_1600_plus_pct} (n={v.dpi_n})")
            if v.dpi_400_count is not None and v.dpi_800_count is not None:
                combo = v.dpi_400_count + v.dpi_800_count
                lines.append(f"- 400 + 800 DPI together: {combo}/{v.dpi_n} ({combo / v.dpi_n * 100:.1f}%).")
            lines.append("")
        if v.polling_n:
            lines.append("### Mouse polling rate")
            lines.append("")
            lines.append(fig("polling"))
            lines.append("")
            lines.append(f"- 1000 Hz: {v.polling_1000_pct} · 2000 Hz: {v.polling_2000_pct} · 4000 Hz: {v.polling_4000_pct} · 8000 Hz: {v.polling_8000_pct} (n={v.polling_n})")
            if v.polling_4000_plus_count is not None:
                lines.append(f"- 4000 Hz and above: {v.polling_4000_plus_count}/{v.polling_n} ({v.polling_4000_plus_pct}).")
            lines.append("")

    # 3. resolution & display
    if v.aspect_n or v.resolution_n:
        lines.append(heading("Resolution & display"))
        lines.append("")
        if v.aspect_rank:
            lines.append("### Aspect ratio")
            lines.append("")
            lines.append(fig("aspect_ratio"))
            lines.append("")
            top, tc, tt = v.aspect_rank[0]
            lines.append(f"- {top}: **{_cats_pct_from_row(v.aspect_rank[0])}** (n={v.aspect_n})")
            if len(v.aspect_rank) > 1:
                runner, rc, rt = v.aspect_rank[1]
                lines.append(f"- {runner} is the next tier at {rc}/{rt} ({_cats_pct_from_row(v.aspect_rank[1])}).")
            lines.append("")
        if v.resolution_rank:
            lines.append("### Resolution")
            lines.append("")
            lines.append(fig("resolution"))
            lines.append("")
            top, tc, tt = v.resolution_rank[0]
            lines.append(f"- Most common: **{top}** ({_cats_pct_from_row(v.resolution_rank[0])}, n={v.resolution_n})")
            if len(v.resolution_rank) > 1:
                runner, rc, rt = v.resolution_rank[1]
                lines.append(f"- {runner} is next at {rc}/{rt} ({_cats_pct_from_row(v.resolution_rank[1])}).")
            lines.append("")

    # 4. crosshair
    if v.crosshair_n:
        lines.append(heading("Crosshair"))
        lines.append("")
        lines.append(fig("crosshair"))
        lines.append("")
        lines.append(f"- Dot and Outline both disabled: **{v.crosshair_minimal_pct}** (n={v.crosshair_n})")
        if v.crosshair_color_rows:
            color_txt = " · ".join(f"{k} {_cats_pct_from_row((k, c, t))}" for k, c, t in v.crosshair_color_rows)
            lines.append(f"- Color categories: {color_txt} (n={v.crosshair_n})")
            lines.append("- The current snapshot only records color categories; the Custom RGB breakdown is not part of the v2 aggregate yet.")
        lines.append("")

    # 5. viewmodel
    if v.fov_n:
        lines.append(heading("Viewmodel"))
        lines.append("")
        lines.append(fig("viewmodel"))
        lines.append("")
        lines.append(f"- `viewmodel_fov 68`: **{v.fov68_pct}** (n={v.fov_n})")
        lines.append(f"- Dominant offset: **{v.viewmodel_dominant_offset}**")
        lines.append("")

    # 6. radar / other
    if v.radar_centered_available:
        lines.append(heading("Radar / Other"))
        lines.append("")
        lines.append("### Radar centered")
        lines.append("")
        lines.append(f"- Enabled: {v.radar_centered_pct} (n={v.radar_centered_n})")
        lines.append("")

    # 7. extended segments (real values only)
    if v.segment_rows:
        lines.append(heading("Extended segments"))
        lines.append("")
        lines.append("| Segment | Teams | Players | Median eDPI |")
        lines.append("|---|---:|---:|---:|")
        seg_labels = {"consensus": "VRS ∩ HLTV Consensus",
                      "ranked_union": "Ranked Union",
                      "core_plus_watchlist": "Core + Watchlist",
                      "all_tracked": "All tracked"}
        for row in v.segment_rows:
            lines.append(f"| {seg_labels[row['key']]} | {row['teams']} | {row['players']} | {row['edpi']} |")
        lines.append("")

    # 8. changes since previous snapshot (conditional)
    if not v.first_snapshot:
        lines.append(heading("Changes since previous snapshot"))
        lines.append("")
        lines.append(f"- Previous snapshot: {v.previous_snapshot}")
        lines.append(f"- Core cohort: {v.previous_player_count} → {v.player_count} players")
        lines.append(f"- Roster turnover: {v.roster_turnover}")
        lines.append(f"- Matched players: {v.matched_count}")
        if v.longitudinal_changes:
            lines.append("")
            for c in v.longitudinal_changes:
                lines.append(f"- {c}")
        if v.matched_panel_summary:
            lines.append("")
            lines.append("Matched panel (same players in both snapshots):")
            for s in v.matched_panel_summary:
                lines.append(f"- {s}")
        lines.append("")

    # 8. data coverage
    lines.append(heading("Data coverage"))
    lines.append("")
    lines.append("| Field | valid_n / cohort |")
    lines.append("|---|---|")
    for key, valid_n, cohort_n in v.field_rows:
        lines.append(f"| {FIELD_LABELS_EN[key]} | {valid_n} / {cohort_n} |")
    lines.append("")
    lines.append(f"{v.players_with_any_setting} Core players currently have at least one usable settings field.")
    lines.append("")

    # source conflicts (only when real conflicts exist)
    if v.conflict_count:
        lines.append("## Source conflicts")
        lines.append("")
        lines.append(f"- {v.conflict_count} field-level conflicts were detected between sources; the primary value was selected per field priority.")
        lines.append("")

    # 9. data & code
    lines.append(heading("Data & code"))
    lines.append("")
    lines.append(f"- Snapshot date: {v.snapshot_date}")
    lines.append(f"- Source: {', '.join(v.source_lines)}")
    lines.append(f"- Snapshot data: [`{v.data_link}`](../{v.data_link})")
    lines.append("- Project & methodology: [`README.md`](../README.md)")
    lines.append("")
    return "\n".join(lines)


def _render_zh(v: ReportView, cross_link_base: str = "latest") -> str:
    fig = lambda k: _figure(v, k)  # noqa: E731
    sec = 0

    def heading(title: str) -> str:
        nonlocal sec
        sec += 1
        return f"## {sec}. {title}"

    lines: list[str] = []
    lines.append(f"# CS2 职业选手设置月度快照 — {v.snapshot_month}")
    lines.append("")
    lines.append(f"[English version](./{cross_link_base}.md)")
    lines.append("")
    meta = f"{v.snapshot_date} · VRS Top 30（{v.core_snapshot_date}）· {v.team_count} 支战队 · {v.player_count} 名选手 · 设置覆盖 {v.players_with_any_setting}"
    if v.first_snapshot:
        meta += f" · `{v.series_id}` baseline"
    else:
        meta += f" · `{v.series_id}`"
    lines.append(meta)
    lines.append("")

    key_rows = _key_numbers_zh(v)
    if key_rows:
        lines.append(heading("本期核心数据"))
        lines.append("")
        lines.extend(key_rows)
        lines.append("")

    if v.edpi_n or v.dpi_n or v.polling_n:
        lines.append(heading("鼠标与灵敏度"))
        lines.append("")
        if v.edpi_n:
            lines.append("### eDPI")
            lines.append("")
            lines.append(fig("edpi"))
            lines.append("")
            lines.append(f"- 中位数：**{v.edpi_median}** · 平均值：**{v.edpi_mean}** · 有效样本：{v.edpi_n}")
            if v.edpi_core_label:
                lines.append(f"- {v.edpi_core_label} eDPI 覆盖 {v.edpi_core_count / v.edpi_core_total * 100:.1f}% 的有效样本（{v.edpi_core_count}/{v.edpi_core_total}）。")
            lines.append("")
        if v.dpi_n:
            lines.append("### DPI")
            lines.append("")
            lines.append(fig("dpi"))
            lines.append("")
            lines.append(f"- 800：**{v.dpi_800_pct}** · 400：{v.dpi_400_pct} · 1600+：{v.dpi_1600_plus_pct}（n={v.dpi_n}）")
            if v.dpi_400_count is not None and v.dpi_800_count is not None:
                combo = v.dpi_400_count + v.dpi_800_count
                lines.append(f"- 400 与 800 DPI 合计 {combo}/{v.dpi_n}（{combo / v.dpi_n * 100:.1f}%）。")
            lines.append("")
        if v.polling_n:
            lines.append("### 鼠标回报率")
            lines.append("")
            lines.append(fig("polling"))
            lines.append("")
            lines.append(f"- 1000 Hz：{v.polling_1000_pct} · 2000 Hz：{v.polling_2000_pct} · 4000 Hz：{v.polling_4000_pct} · 8000 Hz：{v.polling_8000_pct}（n={v.polling_n}）")
            if v.polling_4000_plus_count is not None:
                lines.append(f"- 4000 Hz 及以上合计 {v.polling_4000_plus_count}/{v.polling_n}（{v.polling_4000_plus_pct}）。")
            lines.append("")

    if v.aspect_n or v.resolution_n:
        lines.append(heading("分辨率与显示"))
        lines.append("")
        if v.aspect_rank:
            lines.append("### 宽高比")
            lines.append("")
            lines.append(fig("aspect_ratio"))
            lines.append("")
            top, tc, tt = v.aspect_rank[0]
            lines.append(f"- {top}：**{_cats_pct_from_row(v.aspect_rank[0])}**（n={v.aspect_n}）")
            if len(v.aspect_rank) > 1:
                runner, rc, rt = v.aspect_rank[1]
                lines.append(f"- {runner} 次之，占 {rc}/{rt}（{_cats_pct_from_row(v.aspect_rank[1])}）。")
            lines.append("")
        if v.resolution_rank:
            lines.append("### 分辨率")
            lines.append("")
            lines.append(fig("resolution"))
            lines.append("")
            top, tc, tt = v.resolution_rank[0]
            lines.append(f"- 最常见：**{top}**（{_cats_pct_from_row(v.resolution_rank[0])}，n={v.resolution_n}）")
            if len(v.resolution_rank) > 1:
                runner, rc, rt = v.resolution_rank[1]
                lines.append(f"- {runner} 次之，占 {rc}/{rt}（{_cats_pct_from_row(v.resolution_rank[1])}）。")
            lines.append("")

    if v.crosshair_n:
        lines.append(heading("准星"))
        lines.append("")
        lines.append(fig("crosshair"))
        lines.append("")
        lines.append(f"- Dot 与 Outline 同时关闭：**{v.crosshair_minimal_pct}**（n={v.crosshair_n}）")
        if v.crosshair_color_rows:
            color_txt = " · ".join(f"{k} {_cats_pct_from_row((k, c, t))}" for k, c, t in v.crosshair_color_rows)
            lines.append(f"- 颜色类别：{color_txt}（n={v.crosshair_n}）")
            lines.append("- 当前标准化快照仅按类别统计颜色，尚未包含 Custom RGB 具体色值的拆分。")
        lines.append("")

    if v.fov_n:
        lines.append(heading("Viewmodel"))
        lines.append("")
        lines.append(fig("viewmodel"))
        lines.append("")
        lines.append(f"- `viewmodel_fov 68`：**{v.fov68_pct}**（n={v.fov_n}）")
        lines.append(f"- 最常见三轴偏移：**{v.viewmodel_dominant_offset}**")
        lines.append("")

    if v.radar_centered_available:
        lines.append(heading("Radar / 其他"))
        lines.append("")
        lines.append("### Radar centered")
        lines.append("")
        lines.append(f"- 开启比例：{v.radar_centered_pct}（n={v.radar_centered_n}）")
        lines.append("")

    if v.segment_rows:
        lines.append(heading("扩展样本"))
        lines.append("")
        lines.append("| Segment | 战队 | 选手 | eDPI 中位数 |")
        lines.append("|---|---:|---:|---:|")
        seg_labels = {"consensus": "VRS ∩ HLTV Consensus",
                      "ranked_union": "Ranked Union",
                      "core_plus_watchlist": "Core + Watchlist",
                      "all_tracked": "All tracked"}
        for row in v.segment_rows:
            lines.append(f"| {seg_labels[row['key']]} | {row['teams']} | {row['players']} | {row['edpi']} |")
        lines.append("")

    if not v.first_snapshot:
        lines.append(heading("相比上期"))
        lines.append("")
        lines.append(f"- 上一期：{v.previous_snapshot}")
        lines.append(f"- Core cohort：{v.previous_player_count} → {v.player_count} 名选手")
        lines.append(f"- roster turnover：{v.roster_turnover}")
        lines.append(f"- matched players：{v.matched_count}")
        if v.longitudinal_changes:
            lines.append("")
            for c in v.longitudinal_changes:
                lines.append(f"- {c}")
        if v.matched_panel_summary:
            lines.append("")
            lines.append("同选手 matched panel（两期均在样本中的选手）：")
            for s in v.matched_panel_summary:
                lines.append(f"- {s}")
        lines.append("")

    lines.append(heading("数据覆盖"))
    lines.append("")
    lines.append("| 字段 | valid_n / cohort |")
    lines.append("|---|---|")
    for key, valid_n, cohort_n in v.field_rows:
        lines.append(f"| {FIELD_LABELS_ZH[key]} | {valid_n} / {cohort_n} |")
    lines.append("")
    lines.append(f"当前 {v.players_with_any_setting} 名 Core 选手至少有一项可用设置字段。")
    lines.append("")

    if v.conflict_count:
        lines.append("## Source conflicts")
        lines.append("")
        lines.append(f"- 检测到 {v.conflict_count} 处字段级来源冲突；系统按 field priority 采用主值。")
        lines.append("")

    lines.append(heading("数据与代码"))
    lines.append("")
    lines.append(f"- 数据日期：{v.snapshot_date}")
    lines.append(f"- 数据来源：{', '.join(v.source_lines)}")
    lines.append(f"- 快照数据：[`{v.data_link}`](../{v.data_link})")
    lines.append("- 项目与方法：[`README.md`](../README.md)")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# README current-snapshot block (the ONLY automation-editable README region)
# ---------------------------------------------------------------------------

CURRENT_SNAPSHOT_START = "<!-- CURRENT_SNAPSHOT:START -->"
CURRENT_SNAPSHOT_END = "<!-- CURRENT_SNAPSHOT:END -->"


def render_current_snapshot_block(
    metrics: dict,
    locale: str = "en",
    first_snapshot: Optional[bool] = None,
) -> str:
    """Render the README current-snapshot block from the candidate/accepted
    aggregate. English and Chinese share the same data logic (raw category
    counts); only wording differs. `first_snapshot=None` omits the
    "first baseline" phrasing entirely.

    The WHOLE region between the markers is generated: the header + data
    bullets, the snapshot-specific takeaway sentence (built from the same
    top categories, never hard-coded) and the report links including the
    CURRENT month's archive link (derived from the snapshot date). Nothing
    snapshot-specific may live outside this block.
    """
    agg = metrics.get("aggregate", metrics) if isinstance(metrics, dict) else {}
    series = (agg.get("series") or {}).get("series_id", "n/a")
    snapshot_date = agg.get("snapshot_date") or "n/a"
    team_count = agg.get("team_count")
    player_count = agg.get("player_count") or 0
    av = agg.get("settings_availability") or {}
    m = av.get("players_with_any_setting")
    n = av.get("cohort_players")
    share = av.get("any_setting_share")
    avail_txt = f"{m}/{n}" if m is not None and n is not None else "n/a"
    avail_pct = _pct(share if isinstance(share, (int, float)) else None)

    # shared data logic: one computation, both locales
    edpi = agg.get("edpi") or {}
    edpi_median = edpi.get("median")
    dpi_cats = (agg.get("dpi") or {}).get("categories") or {}
    dpi_combo = _cats_combined_share(dpi_cats, ["400", "800"])
    aspect_rows = _cats_top_rows((agg.get("aspect_ratio") or {}).get("categories") or {})
    res_rows = _cats_top_rows((agg.get("resolution") or {}).get("categories") or {})
    poll_cats = (agg.get("mouse_polling") or {}).get("categories") or {}
    p1000 = _cats_combined_share(poll_cats, ["1000"])
    p4000 = _cats_ge_share(poll_cats, 4000)
    vm = agg.get("viewmodel") or {}
    fov68 = vm.get("fov68_share")
    month = (snapshot_date or "")[:7]

    # takeaway parts are the same top categories the bullets show; when the
    # data changes next month the sentence changes with it
    takeaway_parts = []
    if edpi_median is not None:
        takeaway_parts.append(f"{_num(edpi_median)} eDPI")
    if aspect_rows:
        takeaway_parts.append(aspect_rows[0][0])
    if res_rows:
        takeaway_parts.append(res_rows[0][0])
    if fov68 is not None:
        takeaway_parts.append("FOV 68")

    lines = [CURRENT_SNAPSHOT_START]
    if locale == "zh-CN":
        header = f"**{snapshot_date} · VRS Top 30 · {team_count} 支战队 · {player_count} 名选手**"
        if first_snapshot is True:
            header += f" —— `{series}` 系列的首个正式基线。"
        elif first_snapshot is False:
            header += f" · `{series}`"
        lines.append(header)
        lines.append("")
        if avail_txt != "n/a":
            lines.append(f"- {avail_txt} 名选手有可用设置数据（{avail_pct}）")
        if edpi_median is not None:
            lines.append(f"- 中位 eDPI {_num(edpi_median)}")
        if dpi_combo:
            c, t = dpi_combo
            lines.append(f"- 400 + 800 DPI 合计 {c / t * 100:.1f}%")
        if aspect_rows:
            lines.append(f"- {aspect_rows[0][0]} 占 {_cats_pct_from_row(aspect_rows[0])}")
        if res_rows:
            lines.append(f"- {res_rows[0][0]} 占 {_cats_pct_from_row(res_rows[0])}")
        if p1000:
            c, t = p1000
            lines.append(f"- 1000 Hz 占 {c / t * 100:.1f}%")
        if p4000:
            c, t = p4000
            lines.append(f"- 4000 Hz+ 占 {c / t * 100:.1f}%")
        if fov68 is not None:
            lines.append(f"- viewmodel_fov 68 占 {_pct(fov68)}")
        if takeaway_parts:
            joined = "、".join(takeaway_parts[:-1]) + (
                f" 和 {takeaway_parts[-1]}" if len(takeaway_parts) > 1
                else takeaway_parts[0])
            lines.append("")
            lines.append(f"从当前快照来看，{joined} 依然构成非常稳定的职业赛场主流画像。")
        links = "[最新中文报告](./reports/latest.zh-CN.md) · [English report](./reports/latest.md)"
        if re.fullmatch(r"\d{4}-\d{2}", month):
            links += f" · [月度存档](./reports/{month}.zh-CN.md)"
        lines.append("")
        lines.append(f"→ {links}")
    else:
        header = f"**{snapshot_date} · VRS Top 30 · {team_count} teams · {player_count} players**"
        if first_snapshot is True:
            header += f" — the first accepted `{series}` baseline."
        elif first_snapshot is False:
            header += f" · `{series}`"
        lines.append(header)
        lines.append("")
        if avail_txt != "n/a":
            lines.append(f"- {avail_txt} players with usable settings ({avail_pct})")
        if edpi_median is not None:
            lines.append(f"- median eDPI {_num(edpi_median)}")
        if dpi_combo:
            c, t = dpi_combo
            lines.append(f"- 400 + 800 DPI = {c / t * 100:.1f}%")
        if aspect_rows:
            lines.append(f"- {aspect_rows[0][0]} = {_cats_pct_from_row(aspect_rows[0])}")
        if res_rows:
            lines.append(f"- {res_rows[0][0]} = {_cats_pct_from_row(res_rows[0])}")
        if p1000:
            c, t = p1000
            lines.append(f"- 1000 Hz = {c / t * 100:.1f}%")
        if p4000:
            c, t = p4000
            lines.append(f"- 4000 Hz+ = {c / t * 100:.1f}%")
        if fov68 is not None:
            lines.append(f"- viewmodel_fov 68 = {_pct(fov68)}")
        if takeaway_parts:
            joined = ", ".join(takeaway_parts[:-1]) + (
                f" and {takeaway_parts[-1]}" if len(takeaway_parts) > 1
                else takeaway_parts[0])
            verb = "forms" if len(takeaway_parts) == 1 else "form"
            lines.append("")
            lines.append(f"From the current snapshot, {joined} still {verb} a "
                         "remarkably stable picture of the pro-scene mainstream.")
        links = "[Latest report](./reports/latest.md) · [中文报告](./reports/latest.zh-CN.md)"
        if re.fullmatch(r"\d{4}-\d{2}", month):
            links += f" · [Monthly archive](./reports/{month}.md)"
        lines.append("")
        lines.append(f"→ {links}")
    lines.append(CURRENT_SNAPSHOT_END)
    return "\n".join(lines)


def _cats_ge_share(cats: dict, min_value: float) -> Optional[tuple[int, int]]:
    """(combined_count, total) of categories with numeric key >= min_value."""
    total = sum(cats.values())
    if total <= 0:
        return None
    num = 0
    for k, v in cats.items():
        try:
            if float(k) >= min_value:
                num += v
        except (TypeError, ValueError):
            continue
    return (num, total)


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def render_report(
    metrics: dict,
    drift: Any,
    source_status: dict,
    conflicts: list[dict],
    baseline: Optional[dict] = None,
    roster_report: Optional[dict] = None,
    locale: str = "en",
    manifest: Optional[dict] = None,
    legacy_snapshot: Optional[dict] = None,
    figure_scope: str = "latest",
    cross_link_base: str = "latest",
) -> str:
    """Render the deterministic snapshot report for one locale.

    Both locales share build_report_view(); only the wording differs.
    `locale="en"` is the canonical report, `locale="zh-CN"` the Chinese one.
    `cross_link_base` names the sibling report file (e.g. "2026-08" for the
    archived monthly reports, "latest" for the rolling latest reports).
    """
    view = build_report_view(
        metrics, drift, source_status, conflicts,
        baseline=baseline, roster_report=roster_report, manifest=manifest,
        legacy_snapshot=legacy_snapshot, figure_scope=figure_scope,
        locale=locale,
    )
    if locale == "zh-CN":
        return _render_zh(view, cross_link_base=cross_link_base)
    return _render_en(view, cross_link_base=cross_link_base)
