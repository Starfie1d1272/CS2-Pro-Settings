"""Report determinism."""
from cs2_pro_settings.drift import compute_drift
from cs2_pro_settings.metrics import compute_metrics
from cs2_pro_settings.models import NormalizedPlayerSettings
from cs2_pro_settings.report import render_report


def p(player_id, **kw):
    base = dict(player_id=player_id, canonical_name=player_id)
    base.update(kw)
    return NormalizedPlayerSettings(**base)


def make_inputs():
    players = [
        p("steam:1", dpi=800.0, edpi=800.0, resolution="1280x960", crosshair_color="Custom"),
        p("steam:2", dpi=400.0, edpi=800.0, resolution="1920x1080", crosshair_color="Cyan"),
        p("steam:3", dpi=800.0, edpi=1000.0, resolution="1280x960", crosshair_color="Custom"),
    ]
    metrics = compute_metrics(players, "2026-08-01", scope={"scope_id": "x", "tracked_teams": [], "tracked_team_count": 3})
    baseline = compute_metrics(players, "2026-05-05", scope={"scope_id": "x", "tracked_teams": [], "tracked_team_count": 3})
    drift = compute_drift(baseline, metrics)
    return metrics, drift


def test_report_byte_for_byte_deterministic():
    metrics, drift = make_inputs()
    a = render_report(metrics, drift, {"cs2settings": "ok"}, [])
    b = render_report(metrics, drift, {"cs2settings": "ok"}, [])
    assert a == b
    assert isinstance(a, str)


def test_report_contains_key_sections():
    metrics, drift = make_inputs()
    text = render_report(metrics, drift, {"cs2settings": "ok"}, [])
    for section in ("## Snapshot", "## Source status", "## Key metrics",
                    "## Comparison with previous accepted snapshot",
                    "## Source conflicts", "## Limitations"):
        assert section in text
    assert "snapshot date" in text


def test_report_contains_valid_n():
    metrics, drift = make_inputs()
    text = render_report(metrics, drift, {"cs2settings": "ok"}, [])
    assert "(n=" in text  # every share carries its valid_n
