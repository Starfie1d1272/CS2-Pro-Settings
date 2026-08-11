"""Report semantics regressions.

A. added/removed from a PUBLIC legacy baseline are "unavailable" (privacy
   model strips identity lists) — the report must never fabricate counts
   from the string (the len("unavailable") == 11 bug) and cohort counts
   must come from NUMERIC fields only.
B. non-Core tracked teams must never be labeled "Watchlist + Supplemental".
C. conflict lines never render player_ids (privacy); a conflict section is
   only generated when real conflicts exist.
"""
from cs2_pro_settings.metrics import compute_metrics
from cs2_pro_settings.models import NormalizedPlayerSettings
from cs2_pro_settings.report import render_report


def _players(n: int) -> list[NormalizedPlayerSettings]:
    out = []
    for i in range(n):
        out.append(NormalizedPlayerSettings(
            player_id=f"steam:{i}", canonical_name=f"p{i}", team="vitality",
            dpi=800.0, resolution="1280x960", polling_rate=1000,
            edpi=800.0, max_fps=400, refresh_rate=240,
            crosshair_color="green", crosshair_style="4",
            viewmodel_fov=68.0, radar_rotating=True, radar_zoom=1.0))
    return out


def _metrics(players=None, date="2026-08-11") -> dict:
    metrics = compute_metrics(players or _players(133), date)
    metrics["aggregate"]["series"] = {"series_id": "vrs-core-v2",
                                      "cohort_semantics": "core_top30"}
    metrics["aggregate"]["scope"] = {
        "core_snapshot": "2026-08-10", "core_team_count": 30,
        "tracked_team_count": 37, "scope_id": "vrs-core-v2",
        "tracked_teams": []}
    return metrics


def _baseline_metrics() -> dict:
    b = _metrics(date="2026-08-01")
    b["panel"] = {"status": "unavailable", "player_ids": []}
    return b


def _drift(added=None, removed=None, baseline_date="2026-08-01") -> dict:
    return {
        "baseline_snapshot_date": baseline_date,
        "current_snapshot_date": "2026-08-11",
        "scope_changed": False,
        "level": 1,
        "changed_metrics": [],
        "cohort_change": {
            "baseline_players": 149, "current_players": 133,
            "player_count_delta": -16,
            "added": added, "removed": removed,
        },
        "matched_panel_change": {"status": "unavailable", "matched_count": 0,
                                 "note": "no overlap"},
    }


def _report(added=None, removed=None, locale="en", conflicts=None) -> str:
    metrics = _metrics()
    drift = _drift(added=added, removed=removed)
    return render_report(metrics, drift,
                         {"cs2settings": "ok"}, conflicts or [],
                         baseline=_baseline_metrics(),
                         roster_report={"status": "ok"}, locale=locale)


def test_legacy_baseline_added_removed_never_len_counted():
    """A1: 'unavailable' never len()-counted (the 11 bug); no added/removed
    count is fabricated from the string in either locale."""
    for locale in ("en", "zh-CN"):
        out = _report("unavailable", "unavailable", locale=locale)
        assert "added: 11" not in out
        assert "removed: 11" not in out


def test_none_added_removed_render_unavailable_without_exception():
    """A3: None/missing must not crash and must not fake a count."""
    out = _report(None, None)
    assert "added: 11" not in out
    assert "removed: 11" not in out


def test_cohort_counts_come_from_numeric_fields():
    """A2: cohort change counts render from numeric baseline/current player
    counts, in both locales."""
    out = _report("unavailable", "unavailable", locale="en")
    assert "Core cohort: 149 → 133 players" in out
    zh = _report("unavailable", "unavailable", locale="zh-CN")
    assert "Core cohort：149 → 133 名选手" in zh


def test_non_core_label_neutral():
    """B: the neutral segment name is used, never 'Watchlist + Supplemental'."""
    out = _report()
    assert "Watchlist + Supplemental" not in out


def test_conflicts_section_only_when_real_conflicts_exist():
    """C1: conflict_count == 0 -> no conflict section at all."""
    out = _report()
    assert "Source conflicts" not in out
    assert "field-level conflicts" not in out


def test_conflicts_never_render_player_ids():
    """C2: the conflict hint shows a count only, never player_id / field
    details, in either locale."""
    metrics = _metrics()
    conflicts = [{
        "player_id": "steam:76561198000000000", "field": "dpi",
        "source_a": "cs2settings", "value_a": "800",
        "source_b": "prosettings", "value_b": "400",
    }]
    for locale, marker in (("en", "field-level conflicts"),
                           ("zh-CN", "来源冲突")):
        out = render_report(metrics, _drift(), {"cs2settings": "ok"}, conflicts,
                            baseline=_baseline_metrics(), locale=locale)
        assert marker in out
        assert "steam:" not in out
        assert "76561198000000000" not in out
