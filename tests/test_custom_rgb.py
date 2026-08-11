"""Custom crosshair RGB analysis tests.

Semantic contract (empirically verified 2026-08-11):
- cs2settings `crosshair.color` IS the game's cl_crosshaircolor value
  (share-code codec emits `cl_crosshaircolor <color>` verbatim, `color & 7`
  on encode); verified labels are 1 Red / 2 Green / 3 Yellow / 4 Blue /
  5 Custom / 6 Magenta / 7 White / 8 Orange (front-end preview palette).
- colorR/G/B are the raw cl_crosshaircolor_r/g/b channels. They are ACTIVE
  only in Custom mode (code 5). In preset modes they are latent state and
  never override the preset category and never enter the Custom RGB
  aggregate.
- custom_rgb.valid_n = Custom-mode players with ALL THREE channels.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cs2_pro_settings.metrics import compute_metrics  # noqa: E402
from cs2_pro_settings.models import NormalizedPlayerSettings  # noqa: E402
from cs2_pro_settings.report import render_report  # noqa: E402
from cs2_pro_settings.sources.cs2settings import (  # noqa: E402
    CS2SettingsSource,
    _COLOR_CODES,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _parsed(crosshair: dict):
    """Run a blob crosshair object through the adapter's field mapping."""
    src = CS2SettingsSource()
    blob = {"steamId": "76561198000000001", "displayName": "P",
            "crosshair": crosshair}
    return src._blob_to_parsed("p1", "https://cs2settings.com/players/p1", blob)


def _player(pid, *, color=None, code=None, rgb=None):
    """NormalizedPlayerSettings with optional crosshair color/code/RGB."""
    base = dict(player_id=pid, canonical_name=pid, team="vitality",
                crosshair_dot=False, crosshair_outline=False)
    if color is not None:
        base["crosshair_color"] = color
    if code is not None:
        base["crosshair_color_code"] = code
    if rgb is not None:
        base["crosshair_color_r"], base["crosshair_color_g"], base["crosshair_color_b"] = rgb
    return NormalizedPlayerSettings(**base)  # type: ignore[arg-type]


def _metrics_with(players):
    return compute_metrics(players, "2026-09-01")


def _self_drift(metrics):
    date_ = metrics["aggregate"]["snapshot_date"]
    return {
        "level": 0, "changed_metrics": [],
        "cohort_change": {"baseline_players": 0, "current_players": 0,
                          "player_count_delta": 0, "added": "unavailable",
                          "removed": "unavailable"},
        "matched_panel_change": {"status": "unavailable", "matched_count": 0,
                                 "note": "no overlap"},
        "baseline_snapshot_date": date_, "current_snapshot_date": date_,
        "scope_changed": False, "cohort_stability": "unavailable",
        "roster_turnover_rate": None, "headline_suppressed": False,
        "series_compatible": True, "baseline_incompatible_reason": "",
    }


# ---------------------------------------------------------------------------
# 1. source: Custom color + RGB parse
# ---------------------------------------------------------------------------

def test_custom_code_parses_rgb():
    parsed = _parsed({"style": 4, "color": 5, "colorR": 0, "colorG": 255,
                      "colorB": 145})
    assert parsed.fields["crosshair_color"] == "Custom"
    assert parsed.fields["crosshair_color_code"] == 5
    assert parsed.fields["crosshair_color_r"] == 0
    assert parsed.fields["crosshair_color_g"] == 255
    assert parsed.fields["crosshair_color_b"] == 145


# ---------------------------------------------------------------------------
# 2. source: preset color + stale mismatching RGB (latent, never effective)
# ---------------------------------------------------------------------------

def test_preset_code_with_stale_mismatching_rgb():
    """code 2 = Yellow (verified 0-based game semantics); RGB 255,0,255 is
    a latent stale value from a previous Custom mode. Category stays
    Yellow; RGB is preserved as raw."""
    parsed = _parsed({"color": 2, "colorR": 255, "colorG": 0, "colorB": 255})
    assert parsed.fields["crosshair_color"] == "Yellow"
    assert parsed.fields["crosshair_color_code"] == 2
    assert parsed.fields["crosshair_color_r"] == 255
    assert parsed.fields["crosshair_color_g"] == 0
    assert parsed.fields["crosshair_color_b"] == 255


# ---------------------------------------------------------------------------
# 3. source: RGB channel missing -> field-level fail closed, page survives
# ---------------------------------------------------------------------------

def test_rgb_channel_missing_fails_field_only():
    parsed = _parsed({"color": 5, "colorR": 0, "colorG": 255})  # no colorB
    assert parsed.fields["crosshair_color"] == "Custom"
    assert parsed.fields["crosshair_color_r"] == 0
    assert parsed.fields["crosshair_color_g"] == 255
    assert "crosshair_color_b" not in parsed.fields


# ---------------------------------------------------------------------------
# 4. source: RGB malformed / out of range -> field closed, no page failure
# ---------------------------------------------------------------------------

def test_rgb_malformed_and_out_of_range():
    parsed = _parsed({"color": 5, "colorR": 300, "colorG": "abc", "colorB": None})
    assert parsed.fields["crosshair_color"] == "Custom"
    assert "crosshair_color_r" not in parsed.fields
    assert "crosshair_color_g" not in parsed.fields
    assert "crosshair_color_b" not in parsed.fields


# ---------------------------------------------------------------------------
# 5. source: verified color-code mapping (0-based game semantics)
# ---------------------------------------------------------------------------

def test_verified_color_code_mapping():
    """Only codes with confirmed game semantics are mapped. Verified
    against the Valve CSGO source (weapon_csbase.cpp cl_crosshaircolor
    switch: 0 Red / 1 Green / 2 Yellow / 3 Blue / 4 Cyan / 5 Custom);
    CS2 keeps the same 0-5 values. 6/7/8 are NOT valid cvar states (the
    game falls back to green) and are NOT mapped to color labels."""
    assert _COLOR_CODES == {
        0: "Red", 1: "Green", 2: "Yellow", 3: "Blue", 4: "Cyan", 5: "Custom",
    }
    for code, label in ((0, "Red"), (1, "Green"), (2, "Yellow"),
                        (3, "Blue"), (4, "Cyan"), (5, "Custom")):
        parsed = _parsed({"color": code})
        assert parsed.fields["crosshair_color_code"] == code
        assert parsed.fields["crosshair_color"] == label


def test_unverified_codes_preserve_raw_but_no_label():
    """Codes 6+ are not valid cl_crosshaircolor states (the game falls
    back to green); the site's palette swatches at index 6-8 are UI
    fallback colors, not presets. Raw code is preserved, label is NOT
    guessed (no Magenta / White / Orange locks)."""
    for code in (6, 7, 8):
        parsed = _parsed({"color": code})
        assert parsed.fields["crosshair_color_code"] == code, f"code {code} dropped"
        assert "crosshair_color" not in parsed.fields, f"code {code} got a guessed label"


def test_raw_color_code_zero_preserved():
    """code 0 is a valid raw state (0 Red; share-code codec `color & 7`
    can represent it). It must never be dropped."""
    parsed = _parsed({"color": 0, "colorR": 250, "colorG": 50, "colorB": 50})
    assert parsed.fields["crosshair_color_code"] == 0
    assert parsed.fields["crosshair_color"] == "Red"


def test_share_code_7_bit_boundary_documented():
    """The codec stores `color & 7`: 8 & 7 == 0, so 8 is NOT a distinct
    representable state even though the raw value is preserved."""
    parsed = _parsed({"color": 8})
    assert parsed.fields["crosshair_color_code"] == 8  # raw kept
    assert "crosshair_color" not in parsed.fields      # but 8 != a preset


# ---------------------------------------------------------------------------
# 6. model: RGB round-trip
# ---------------------------------------------------------------------------

def test_model_rgb_round_trip():
    p = _player("steam:1", color="Custom", code=5, rgb=(0, 255, 145))
    d = p.as_dict()
    d.pop("provenance", None)
    p2 = NormalizedPlayerSettings.from_dict(d)
    assert p2.crosshair_color == "Custom"
    assert p2.crosshair_color_code == 5
    assert (p2.crosshair_color_r, p2.crosshair_color_g, p2.crosshair_color_b) == (0, 255, 145)


# ---------------------------------------------------------------------------
# 7. reconcile: provenance preserved for RGB fields
# ---------------------------------------------------------------------------

def test_reconcile_provenance_for_rgb_fields():
    from cs2_pro_settings.models import SourceObservation
    from cs2_pro_settings.reconcile import reconcile

    obs = [
        SourceObservation(player_id="steam:1", source="cs2settings", field="crosshair_color_r",
                          value=0, source_url="https://cs2settings.com/players/donk",
                          retrieved_at="2026-09-01", source_updated_at="2026-08-20"),
        SourceObservation(player_id="steam:1", source="cs2settings", field="crosshair_color_g",
                          value=255, source_url="https://cs2settings.com/players/donk",
                          retrieved_at="2026-09-01", source_updated_at="2026-08-20"),
        SourceObservation(player_id="steam:1", source="cs2settings", field="crosshair_color_b",
                          value=145, source_url="https://cs2settings.com/players/donk",
                          retrieved_at="2026-09-01", source_updated_at="2026-08-20"),
    ]
    result = reconcile(obs, field_priority={"crosshair": ["cs2settings"]},
                       enabled_sources={"cs2settings"})
    s = result.players["steam:1"]
    assert s.crosshair_color_r == 0 and s.crosshair_color_g == 255 and s.crosshair_color_b == 145
    for attr in ("crosshair_color_r", "crosshair_color_g", "crosshair_color_b"):
        prov = s.provenance[attr]
        assert prov["source"] == "cs2settings"
        assert prov["source_url"] == "https://cs2settings.com/players/donk"
        assert prov["retrieved_at"] == "2026-09-01"
        assert prov["source_updated_at"] == "2026-08-20"


# ---------------------------------------------------------------------------
# 8/9/10/11. metrics: only Custom + complete RGB contributes
# ---------------------------------------------------------------------------

def _custom_rgb_fixture_players():
    return [
        _player("steam:1", color="Custom", code=5, rgb=(0, 255, 145)),   # in
        _player("steam:2", color="Custom", code=5, rgb=(255, 255, 255)),  # in
        _player("steam:3", color="Yellow", code=2, rgb=(255, 0, 255)),   # preset stale: OUT
        _player("steam:4", color="Custom", code=5, rgb=(0, 255, None)),  # missing channel: OUT
    ]


def test_only_custom_contributes_to_custom_rgb():
    m = _metrics_with(_custom_rgb_fixture_players())
    crgb = m["aggregate"]["crosshair"]["custom_rgb"]
    assert crgb["valid_n"] == 2
    assert crgb["custom_players"] == 3
    assert crgb["categories"] == {"0,255,145": 1, "255,255,255": 1}
    assert "255,0,255" not in crgb["categories"]  # preset stale RGB excluded


def test_custom_rgb_coverage():
    m = _metrics_with(_custom_rgb_fixture_players())
    crgb = m["aggregate"]["crosshair"]["custom_rgb"]
    assert crgb["coverage"] == 0.6667  # round(2/3, 4) aggregate convention
    assert crgb["unique_colors"] == 2
    assert crgb["top_rgb"] == "0,255,145"  # count desc, key asc tie-break
    assert crgb["top_rgb_share"] == 0.5


def test_custom_rgb_exact_categories_deterministic():
    players = [
        _player(f"steam:{i}", color="Custom", code=5, rgb=(0, 255, 145)) for i in range(3)
    ] + [
        _player(f"steam:{i}", color="Custom", code=5, rgb=(255, 255, 255)) for i in range(3, 5)
    ] + [
        _player(f"steam:{i}", color="Custom", code=5, rgb=(0, 255, 0)) for i in range(5, 7)
    ]
    m1 = _metrics_with(players)
    m2 = _metrics_with(list(reversed(players)))
    assert m1["aggregate"]["crosshair"]["custom_rgb"]["categories"] == \
        m2["aggregate"]["crosshair"]["custom_rgb"]["categories"] == \
        {"0,255,145": 3, "0,255,0": 2, "255,255,255": 2}


def test_no_custom_players_means_empty_rgb_block():
    m = _metrics_with([_player("steam:1", color="Blue"),
                       _player("steam:2", color="Red")])
    crgb = m["aggregate"]["crosshair"]["custom_rgb"]
    assert crgb["valid_n"] == 0
    assert crgb["custom_players"] == 0
    assert crgb["coverage"] is None
    assert crgb["categories"] == {}
    assert crgb["unique_colors"] == 0


def test_custom_detection_uses_mode_code_not_label():
    """The raw mode code is the authoritative switch: a player carrying the
    Custom LABEL but a preset code (e.g. label from another source path)
    is NOT Custom-mode and its RGB never enters the aggregate."""
    m = _metrics_with([
        _player("steam:1", color="Custom", code=2, rgb=(0, 255, 145)),
        _player("steam:2", color="Custom", code=5, rgb=(0, 255, 145)),
    ])
    crgb = m["aggregate"]["crosshair"]["custom_rgb"]
    assert crgb["custom_players"] == 1      # only code 5 counts
    assert crgb["valid_n"] == 1
    assert crgb["categories"] == {"0,255,145": 1}


# ---------------------------------------------------------------------------
# 13/14/15/16. report: RGB subsection
# ---------------------------------------------------------------------------

def test_report_rgb_subsection_appears_with_data():
    m = _metrics_with(_custom_rgb_fixture_players())
    drift = _self_drift(m)
    en = render_report(m, drift, {"cs2settings": "ok"}, [], baseline=m, locale="en")
    zh = render_report(m, drift, {"cs2settings": "ok"}, [], baseline=m, locale="zh-CN")
    assert "Custom RGB: **2/3** players with complete RGB (66.7%)" in en
    assert "Custom RGB：**2/3** 名选手 RGB 三通道完整（66.7%）" in zh
    assert "2 unique exact colors" in en
    assert "2 种精确颜色" in zh
    assert "crosshair_custom_rgb.png" in en
    assert "crosshair_custom_rgb.png" in zh


def test_report_rgb_subsection_hidden_when_no_data():
    m = _metrics_with([_player("steam:1", color="Blue"),
                       _player("steam:2", color="Red")])
    drift = _self_drift(m)
    en = render_report(m, drift, {"cs2settings": "ok"}, [], baseline=m, locale="en")
    zh = render_report(m, drift, {"cs2settings": "ok"}, [], baseline=m, locale="zh-CN")
    assert "Custom RGB" not in en
    assert "Custom RGB" not in zh
    assert "crosshair_custom_rgb.png" not in en
    assert "crosshair_custom_rgb.png" not in zh


def test_report_no_old_rgb_missing_sentence():
    """The 'Custom RGB not part of the aggregate yet' sentence is gone."""
    m = _metrics_with(_custom_rgb_fixture_players())
    drift = _self_drift(m)
    en = render_report(m, drift, {"cs2settings": "ok"}, [], baseline=m, locale="en")
    zh = render_report(m, drift, {"cs2settings": "ok"}, [], baseline=m, locale="zh-CN")
    assert "not part of the v2 aggregate yet" not in en
    assert "尚未包含 Custom RGB" not in zh


# ---------------------------------------------------------------------------
# 17/18. plot: deterministic, only Custom valid RGB input
# ---------------------------------------------------------------------------

def test_plot_custom_rgb_generated_only_with_custom_data(tmp_path):
    from cs2_pro_settings.plots import render_all

    # with Custom data: figure is written
    m = _metrics_with(_custom_rgb_fixture_players())
    out1 = tmp_path / "fig1"
    render_all(m, out1)
    p1 = out1 / "crosshair_custom_rgb.png"
    assert p1.exists() and p1.stat().st_size > 0

    # deterministic: same input -> same bytes (same matplotlib env)
    out2 = tmp_path / "fig2"
    render_all(m, out2)
    assert (out2 / "crosshair_custom_rgb.png").read_bytes() == p1.read_bytes()

    # preset-only: figure NOT written
    m2 = _metrics_with([_player("steam:1", color="Blue", rgb=(255, 0, 255)),
                        _player("steam:2", color="Red")])
    out3 = tmp_path / "fig3"
    render_all(m2, out3)
    assert not (out3 / "crosshair_custom_rgb.png").exists()
