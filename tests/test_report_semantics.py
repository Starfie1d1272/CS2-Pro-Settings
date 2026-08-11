"""Report semantics regressions.

A. added/removed from a PUBLIC legacy baseline are "unavailable" (privacy
   model strips identity lists) — they must render as text, never as a
   len("unavailable") == 11 fake count.
B. non-Core tracked teams must be labeled neutrally (tracked - core), not
   as "Watchlist + Supplemental" (the tracked universe also contains
   reference-only ranked teams).
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


def _report(cc_added, cc_removed, tracked=37, core=30) -> str:
    metrics = compute_metrics(_players(133), "2026-08-11")
    metrics["aggregate"]["series"] = {"series_id": "vrs-core-v2",
                                      "cohort_semantics": "core_top30"}
    metrics["aggregate"]["scope"] = {
        "core_snapshot": "2026-08-10", "core_team_count": core,
        "tracked_team_count": tracked, "scope_id": "vrs-core-v2",
        "tracked_teams": []}
    drift = {
        "baseline_snapshot_date": "2026-05-05",
        "current_snapshot_date": "2026-08-11",
        "scope_changed": True,
        "level": 1,
        "changed_metrics": [],
        "cohort_change": {
            "baseline_players": 198, "current_players": 133,
            "player_count_delta": -65,
            "added": cc_added, "removed": cc_removed,
        },
        "matched_panel_change": {"status": "unavailable"},
    }
    return render_report(metrics, drift, {"cs2settings": "ok"}, [],
                         roster_report={"status": "ok"})


def test_legacy_baseline_added_removed_render_unavailable():
    """A1: 'unavailable' never len()-counted (the 11 bug)."""
    out = _report("unavailable", "unavailable")
    assert "added: unavailable" in out
    assert "removed: unavailable" in out
    assert "added: 11" not in out
    assert "removed: 11" not in out


def test_identity_bearing_added_removed_render_counts():
    """A2: real identity lists render as counts."""
    out = _report(["a", "b", "c"], ["x", "y"])
    assert "added: 3" in out
    assert "removed: 2" in out


def test_none_added_removed_render_unavailable_without_exception():
    """A3: None/missing must not crash and must not fake a count."""
    out = _report(None, None)
    assert "added: unavailable" in out
    assert "removed: unavailable" in out


def test_non_core_tracked_label_neutral():
    """B: neutral label with the real tracked-core difference."""
    out = _report("unavailable", "unavailable")
    assert "Non-Core tracked teams in universe: 7" in out
    assert "Watchlist + Supplemental teams in universe: 7" not in out


def test_non_core_label_tracks_actual_difference():
    """B: label uses the actual difference for other cohort sizes."""
    out = _report("unavailable", "unavailable", tracked=34, core=30)
    assert "Non-Core tracked teams in universe: 4" in out
