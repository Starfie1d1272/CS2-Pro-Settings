"""Deterministic report generation (reports/latest.md).

No LLM/API calls: the report is rendered from metrics + drift JSON.
It contains: snapshot date, cohort size, source status, data freshness, key
metrics, comparison with previous accepted snapshot, current cohort vs matched
panel, detected conclusion changes, limitations.

Interpretive causal conclusions are NOT generated automatically.
"""
from __future__ import annotations

from typing import Any, Optional


def _fmt_share(v: Optional[float]) -> str:
    return f"{v * 100:.1f}%" if v is not None else "n/a"


def _fmt_cats(cats: Optional[dict], valid_n: Optional[int]) -> str:
    if not cats:
        return "n/a"
    parts = []
    for k, v in cats.items():
        parts.append(f"{k} {v}" + (f" ({v / valid_n * 100:.1f}%)" if valid_n else ""))
    return ", ".join(parts)


def render_report(
    metrics: dict,
    drift: Any,
    source_status: dict,
    conflicts: list[dict],
    baseline: Optional[dict] = None,
) -> str:
    agg = metrics["aggregate"]
    panel = metrics.get("panel", {})
    lines: list[str] = []

    lines.append("# CS2 Pro Settings — Latest Snapshot (generated)")
    lines.append("")
    lines.append("> Generated deterministically by `python -m cs2_pro_settings report`.")
    lines.append("> Interpretive conclusions require human review.")
    lines.append("")

    # 1. snapshot + cohort
    lines.append("## Snapshot")
    lines.append("")
    lines.append(f"- snapshot date: **{agg.get('snapshot_date', 'n/a')}**")
    lines.append(f"- cohort size: {agg.get('player_count')} players / {agg.get('team_count')} teams")
    lines.append(f"- source: {agg.get('source', {}).get('primary', 'n/a')}")
    lines.append("")

    # 2. source status + freshness
    lines.append("## Source status")
    lines.append("")
    for src, st in sorted(source_status.items()):
        lines.append(f"- {src}: {st}")
    lines.append("")

    # 3. key metrics (all with valid_n)
    lines.append("## Key metrics")
    lines.append("")
    lines.append("- eDPI: median {m}, mean {mean} (n={n})".format(
        m=agg["edpi"]["median"], mean=agg["edpi"]["mean"], n=agg["edpi"]["count"]))
    dpi = agg["dpi"]
    lines.append(f"- DPI: top {dpi['top_category']} ({_fmt_share(dpi['share_800'])} at 800, n={dpi['valid_n']})")
    res = agg["resolution"]
    lines.append(f"- Resolution: top {res['top_category']} ({_fmt_share(res['share_1280x960'])} at 1280x960, n={res['valid_n']})")
    ar = agg["aspect_ratio"]
    lines.append(f"- Aspect ratio: 4:3 {_fmt_share(ar['share_4_3'])} (n={ar['valid_n']})")
    rr = agg["refresh_rate"]
    lines.append(f"- Refresh rate: 360Hz {_fmt_share(rr['share_360'])}, 540Hz+ {_fmt_share(rr['share_540_plus'])} (n={rr['valid_n']})")
    fps = agg["fps_max"]
    lines.append(f"- fps_max 0 (unlimited): {_fmt_share(fps['unlimited_share'])} (n={fps['valid_n']})")
    ch = agg["crosshair"]
    lines.append(f"- Crosshair: Dot+Outline off {_fmt_share(ch['dot_outline_off_share'])} (n={ch['valid_n']}); top color {ch['top_color']}")
    vm = agg["viewmodel"]
    lines.append(f"- Viewmodel: FOV 68 {_fmt_share(vm['fov68_share'])} (n={vm['valid_n']}); dominant offset {vm['dominant_offset']}")
    radar = agg["radar"]
    lines.append(f"- Radar: rotating {_fmt_share(radar['rotating_share'])}, centered {_fmt_share(radar['centered_share'])} (n={radar['valid_n']})")
    poll = agg["mouse_polling"]
    lines.append(f"- Polling: 4000Hz+ {_fmt_share(poll['share_4000_plus'])} (n={poll['valid_n']})")
    lines.append("")

    # 4. comparison with previous accepted snapshot
    lines.append("## Comparison with previous accepted snapshot")
    lines.append("")
    if drift is None:
        lines.append("- no baseline available")
    else:
        lines.append(f"- baseline: {drift.baseline_snapshot_date} -> current: {drift.current_snapshot_date}")
        lines.append(f"- drift level: **{drift.level}** (0 = data changed, no material drift; 1 = trend drift; 2 = headline conclusion changed)")
        if drift.changed_metrics:
            for c in drift.changed_metrics:
                b, cur = c["baseline"], c["current"]
                if c.get("change_pp") is not None:
                    delta = f"{c['change_pp']:+.1f}pp"
                elif c.get("change") is not None:
                    delta = f"{c['change']:+.1f}"
                else:
                    delta = "changed"
                lines.append(f"- {c['conclusion']}: {b} -> {cur} ({delta}) [level {c['level']}]")
        else:
            lines.append("- no conclusion-level changes")
        lines.append("")
        lines.append("### Cohort change")
        lines.append("")
        cc = drift.cohort_change
        lines.append(f"- baseline players: {cc['baseline_players']}; current: {cc['current_players']}")
        lines.append(f"- added: {len(cc['added'])}; removed: {len(cc['removed'])}")
        lines.append("")
        lines.append("### Matched panel")
        lines.append("")
        mp = drift.matched_panel_change
        lines.append(f"- status: {mp['status']}; matched: {mp.get('matched_count', 0)}")
        if mp.get("per_field"):
            for fld, info in mp["per_field"].items():
                lines.append(f"- {fld}: {info['changed']}/{info['compared']} players changed")
        elif mp.get("note"):
            lines.append(f"- {mp['note']}")
    lines.append("")

    # 5. conflicts
    lines.append("## Source conflicts")
    lines.append("")
    lines.append(f"- total: {len(conflicts)}")
    for c in conflicts[:20]:
        lines.append(f"- {c['player_id']} {c['field']}: {c['source_a']}={c['value_a']} vs {c['source_b']}={c['value_b']}")
    if len(conflicts) > 20:
        lines.append(f"- ... and {len(conflicts) - 20} more")
    lines.append("")

    # 6. limitations
    lines.append("## Limitations")
    lines.append("")
    lines.append("- All statements describe the sampled cohort; prevalence does not imply causal performance benefit.")
    lines.append("- valid_n varies per field; a missing field never defaults to the full cohort size.")
    lines.append("- Automated collection is restricted to sources that allow normal HTTP access (no anti-bot bypass).")
    lines.append("- Row-level third-party data is not distributed; only aggregates and generated analyses are published.")
    lines.append("")

    return "\n".join(lines)
