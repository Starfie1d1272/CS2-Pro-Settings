"""Production-figure regressions: real categories, empty fields, determinism."""
import hashlib

from cs2_pro_settings.plots import render_all


def _full_metrics() -> dict:
    agg = {
        "player_count": 149,
        "edpi": {"count": 149, "median": 800.0,
                 "distribution": {"600-800": 90, "800-1000": 40,
                                  "1600+": 19}},
        "dpi": {"valid_n": 149,
                "categories": {"400": 30, "800": 99, "1600": 20}},
        "zoom_sensitivity": {"valid_n": 148,
                             "categories": {"0.8": 10, "1": 130, "1.1": 8}},
        "mouse_polling": {"valid_n": 149,
                          "categories": {"8000": 9, "1000": 100,
                                         "4000": 30, "2000": 10}},
        "resolution": {"valid_n": 149,
                       "categories": {"1280x960": 70, "1920x1080": 50,
                                      "1024x768": 29}},
        "aspect_ratio": {"valid_n": 149,
                         "categories": {"4:3": 80, "16:9": 69}},
        "scaling_mode": {"valid_n": 149,
                         "categories": {"Stretched": 120, "Native": 29}},
        "boost_player": {"valid_n": 100, "missing_n": 49,
                         "enabled_count": 80, "disabled_count": 20,
                         "enabled_share": 0.8},
        "crosshair": {
            "valid_n": 149, "color_valid_n": 149,
            "color_categories": {"Custom": 80, "Green": 45, "Cyan": 24},
            "custom_rgb": {"valid_n": 3,
                           "categories": {"255,255,255": 2, "0,255,145": 1}},
            "geometry": {
                "style": {"valid_n": 149, "categories": {"4": 148, "5": 1}},
                "size": {"valid_n": 149, "categories": {"1": 90, "2": 59}},
                "gap": {"valid_n": 149, "categories": {"-4": 90, "-3": 59}},
                "thickness": {"valid_n": 149, "categories": {"0": 60, "1": 89}},
                "alpha": {"valid_n": 149, "categories": {"200": 20, "255": 129}},
                "dot": {"valid_n": 120, "enabled_count": 12},
                "outline": {"valid_n": 130, "enabled_count": 26},
            },
        },
        "radar": {"centered_valid_n": 120, "centered_share": 0.75,
                  "zoom": {"valid_n": 99,
                           "categories": {"0.3": 20, "0.4": 60, "0.7": 19}}},
    }
    return {"aggregate": agg, "panel": {"status": "available",
                                          "player_count": 149}}


def test_render_all_produces_compact_production_set(tmp_path):
    written = render_all(_full_metrics(), tmp_path)
    assert {p.name for p in written} == {
        "mouse.png", "display.png", "crosshair_geometry.png",
        "crosshair_color.png", "radar.png",
    }
    for path in written:
        assert path.stat().st_size > 10_000


def test_zero_valid_blocks_do_not_create_empty_figures(tmp_path):
    metrics = {"aggregate": {"player_count": 3,
                              "edpi": {"count": 0, "distribution": {}},
                              "dpi": {"valid_n": 0, "categories": {}},
                              "zoom_sensitivity": {"valid_n": 0, "categories": {}},
                              "mouse_polling": {"valid_n": 0, "categories": {}},
                              "radar": {"centered_valid_n": 0,
                                        "zoom": {"valid_n": 0, "categories": {}}}}}
    assert render_all(metrics, tmp_path) == []
    assert list(tmp_path.glob("*.png")) == []


def test_render_all_is_byte_identical_across_consecutive_runs(tmp_path):
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first = render_all(_full_metrics(), first_dir)
    second = render_all(_full_metrics(), second_dir)
    assert [p.name for p in first] == [p.name for p in second]
    first_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in first}
    second_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in second}
    assert first_hashes == second_hashes
