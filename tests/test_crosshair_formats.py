"""Schema migration regression cases; synthetic data only."""
import pytest

from cs2_pro_settings.sources.cs2settings import CS2SettingsSource
from cs2_pro_settings.models import SourceObservation
from cs2_pro_settings.normalize import normalize_field
from cs2_pro_settings.reconcile import reconcile
from cs2_pro_settings.metrics import compute_metrics
from cs2_pro_settings.drift import _evaluate_conclusion
from cs2_pro_settings.report import render_report


def player(ch, pid="steam:76561198000000001"):
    parsed = CS2SettingsSource()._blob_to_parsed("synthetic", "https://example.test/p", {
        "steamId": pid.split(":")[-1], "crosshair": ch})
    observations = []
    for key, value in parsed.fields.items():
        attr, value = normalize_field(key, value)
        if attr and value is not None:
            observations.append(SourceObservation(pid, attr, value, "cs2settings",
                                                   parsed.source_url, "2026-10-08"))
    return reconcile(observations, {"crosshair": ["cs2settings"]}, {"cs2settings"}).players[pid]


def pixel(**kwargs):
    return dict(format="cs2-v1", colorR=0, colorG=255, colorB=255,
                outlineMode=0, outline=True, screenHeight=960, size=3,
                gap=1, thickness=2, dot=False, code="CS-synthetic", **kwargs)


@pytest.mark.parametrize("fmt", ["cs2-v1", "legacy-v3", "legacy-v4"])
def test_direct_rgb_survives_normalize_and_reconcile(fmt):
    ch = pixel(); ch["format"] = fmt
    p = player(ch)
    assert p.crosshair_color == "Custom"
    assert p.crosshair_color_code is None
    assert p.crosshair_screen_height == 960
    assert p.crosshair_code == "CS-synthetic"
    assert p.provenance["crosshair_format"]["source"] == "cs2settings"
    agg = compute_metrics([p], "2026-10-08")["aggregate"]["crosshair"]
    assert agg["color_valid_n"] == 1
    assert agg["custom_rgb"]["categories"] == {"0,255,255": 1}


@pytest.mark.parametrize("mode,enabled", [(0, False), (1, True), (2, True), (3, None), (1.5, None), (True, None), (None, None)])
def test_outline_mode_authoritative(mode, enabled):
    ch = pixel(); ch["outlineMode"] = mode
    p = player(ch)
    assert p.crosshair_outline is enabled
    agg = compute_metrics([p], "2026-10-08")["aggregate"]["crosshair"]
    assert agg["valid_n"] == (0 if enabled is None else 1)
    assert agg["dot_outline_off_share"] == (None if enabled is None else float(not enabled))


@pytest.mark.parametrize("bad", [None, 256, -1, 1.2, True, "oops"])
def test_incomplete_or_bad_rgb_not_counted(bad):
    ch = pixel(); ch["colorR"] = bad
    agg = compute_metrics([player(ch)], "2026-10-08")["aggregate"]["crosshair"]
    assert agg["color_valid_n"] == 0
    assert agg["custom_rgb"]["valid_n"] == 0
    assert agg["custom_rgb"]["custom_players"] == 1


def test_geometry_never_pools_units_or_reference_heights():
    a = player(pixel(), "steam:1")
    ch = pixel(); ch["screenHeight"] = 768; ch["size"] = 2
    b = player(ch, "steam:2")
    c = player({"color": 4, "size": 1.5, "gap": -3, "thickness": .5}, "steam:3")
    m = compute_metrics([a, b, c], "2026-10-08")
    crosshair = m["aggregate"]["crosshair"]
    assert crosshair["geometry"]["size"]["valid_n"] == 0
    assert m["figure_data"]["crosshair_gap_size"]["valid_n"] == 0
    groups = crosshair["geometry_by_context"]
    assert groups["cs2-v1:px@960"]["size"]["median"] == 3
    assert groups["cs2-v1:px@768"]["size"]["median"] == 2
    assert groups["legacy-units"]["size"]["median"] == 1.5


def test_legacy_presets_ignore_latent_rgb_and_unknown_format_fails_closed():
    legacy = player({"color": 4, "colorR": 255, "colorG": 0, "colorB": 0})
    unknown = pixel(); unknown["format"] = "future-v9"
    p = player(unknown, "steam:2")
    ch = compute_metrics([legacy, p], "2026-10-08")["aggregate"]["crosshair"]
    assert ch["color_categories"] == {"Cyan": 1}
    assert ch["custom_rgb"]["valid_n"] == 0
    assert p.crosshair_outline is None


def test_crosshair_migration_suppresses_only_crosshair_drift():
    baseline = {"crosshair": {"top_color": "Cyan"}, "dpi": {"top_category": "400"}}
    current = {"crosshair": {"measurement_version": "pixel-v2:cs2-v1", "top_color": "Custom"},
               "dpi": {"top_category": "800"}}
    rule = {"metric": "crosshair.top_color", "kind": "categorical"}
    result = _evaluate_conclusion("color", rule, baseline, current)
    assert result["level"] == 0
    assert "new baseline" in result["note"]
    assert _evaluate_conclusion("dpi", {"metric": "dpi.top_category", "kind": "categorical"}, baseline, current)["level"] == 2
    baseline["crosshair"]["measurement_version"] = current["crosshair"]["measurement_version"]
    assert _evaluate_conclusion("color", rule, baseline, current)["level"] == 2


def test_missing_reference_height_never_substitutes_video_resolution():
    ch = pixel(); ch["screenHeight"] = None
    p = player(ch)
    assert p.crosshair_screen_height is None
    m = compute_metrics([p], "2026-10-08")
    group = m["aggregate"]["crosshair"]["geometry_by_context"]["cs2-v1:px@unknown"]
    assert group["size"]["valid_n"] == 0
    assert group["size"]["median"] is None


def test_bilingual_reports_explain_measurement_context():
    m = compute_metrics([player(pixel())], "2026-10-08")
    drift = {"level": 0, "changed_metrics": [], "cohort_change": {},
             "matched_panel_change": {"status": "unavailable"}}
    for locale in ("en", "zh-CN"):
        report = render_report(m, drift, source_status={}, conflicts=[], locale=locale)
        assert "cs2-v1:px@960" in report
        assert "Custom" in report
        assert "(n=1)" in report


@pytest.mark.parametrize("bad", [1.5, True, -1, float("inf"), "unknown"])
def test_new_enum_normalization_rejects_lossy_values(bad):
    assert normalize_field("crosshair_outline_mode", bad) == ("crosshair_outline_mode", None)


def test_malformed_format_does_not_inherit_legacy_semantics():
    ch = pixel(); ch["format"] = ["cs2-v1"]
    p = player(ch)
    assert p.crosshair_format == "unknown"
    assert p.crosshair_color is None
