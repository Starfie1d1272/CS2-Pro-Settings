"""Regression: render_all with NON-EMPTY category dicts.

The `X or {}.items()` precedence bug made the iteration source the dict
ITSELF (keys) whenever categories was a non-empty dict — unpacking a key
string like "800" into (k, v) raised 'too many values to unpack'. Local
offline fixtures had EMPTY categories (falsy), so the bug only surfaced on
live data in the weekly workflow.
"""
import json

import pytest

from cs2_pro_settings.plots import render_all


def _full_metrics() -> dict:
    """Aggregate shaped like a real live run (non-empty categories)."""
    agg = {
        "player_count": 149,
        "team_count": 30,
        "series": {"series_id": "vrs-core-v2", "cohort_semantics": "core"},
        "scope": {"scope_id": "vrs-core-v2", "core_snapshot": "2026-08-10"},
        "edpi": {
            "valid_n": 149, "median": 800.0,
            "distribution": {"600-800": 90, "800-1000": 40, "1600+": 19},
        },
        "dpi": {"valid_n": 149,
                "categories": {"400": 30, "800": 99, "1600": 20},
                "top_category": "800"},
        "resolution": {"valid_n": 149,
                       "categories": {"1280x960": 70, "1920x1080": 50,
                                      "1024x768": 29}},
        "aspect_ratio": {"valid_n": 149, "categories": {"4:3": 80, "16:9": 69}},
        "refresh_rate": {"valid_n": 149, "categories": {"240": 60, "360": 89}},
        "fps_max": {"valid_n": 149, "categories": {"400": 99, "unlimited": 50}},
        "crosshair": {"valid_n": 149, "top_category": "default"},
        "viewmodel": {"valid_n": 149, "top_category": "classic"},
        "radar": {"valid_n": 149},
        "mouse_polling": {"valid_n": 149, "categories": {"1000": 100, "8000": 49}},
    }
    return {"aggregate": agg, "panel": {"status": "available", "player_count": 149}}


def test_render_all_with_nonempty_categories(tmp_path):
    written = render_all(_full_metrics(), tmp_path)
    names = {p.name for p in written}
    assert "dpi.png" in names
    assert "resolution.png" in names
    assert "refresh_rate.png" in names
    assert "polling_rate.png" in names
    assert "edpi.png" in names
    for p in written:
        assert p.stat().st_size > 0


def test_render_all_with_empty_categories_still_ok(tmp_path):
    m = _full_metrics()
    for k in ("dpi", "resolution", "refresh_rate", "mouse_polling"):
        m["aggregate"][k]["categories"] = {}
    written = render_all(m, tmp_path)
    assert written  # no crash, no exception
