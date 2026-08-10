"""Metrics: valid_n denominators, determinism."""
import json

from cs2_pro_settings.metrics import compute_metrics, public_aggregate
from cs2_pro_settings.models import NormalizedPlayerSettings


def p(player_id, **kw):
    base = dict(player_id=player_id, canonical_name=player_id)
    base.update(kw)
    return NormalizedPlayerSettings(**base)


def test_valid_n_not_full_cohort():
    players = [
        p("steam:1", dpi=800.0, edpi=800.0),
        p("steam:2", dpi=400.0, edpi=800.0),
        p("steam:3", dpi=None, edpi=None),  # no settings at all
    ]
    m = compute_metrics(players, "2026-08-01")
    dpi = m["aggregate"]["dpi"]
    assert dpi["valid_n"] == 2
    assert dpi["share_800"] == 0.5  # 1 of 2 valid, NOT 1 of 3
    assert dpi["categories"] == {"800": 1, "400": 1}


def test_missing_field_never_defaults_to_full_cohort():
    players = [
        p("steam:1", dpi=800.0),
        p("steam:2", dpi=800.0),
        p("steam:3", dpi=800.0),
        p("steam:4", dpi=800.0),
        p("steam:5", dpi=None),
    ]
    m = compute_metrics(players, "2026-08-01")
    assert m["aggregate"]["dpi"]["valid_n"] == 4
    assert m["aggregate"]["dpi"]["share_800"] == 1.0  # 4/4 valid


def test_deterministic_output():
    players = [
        p("steam:1", dpi=800.0, resolution="1280x960", crosshair_color="Custom"),
        p("steam:2", dpi=400.0, resolution="1920x1080", crosshair_color="Cyan"),
        p("steam:3", dpi=800.0, resolution="1280x960", crosshair_color="Custom"),
    ]
    a = compute_metrics(players, "2026-08-01")
    b = compute_metrics(players, "2026-08-01")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_categories_sorted_count_desc():
    # tie (3/3) -> key asc
    players = [p(f"steam:{i}", dpi=800.0 if i % 2 else 400.0) for i in range(6)]
    m = compute_metrics(players, "2026-08-01")
    cats = m["aggregate"]["dpi"]["categories"]
    assert list(cats.keys()) == ["400", "800"]
    players2 = [p(f"steam:{i}", dpi=[400.0, 800.0, 800.0, 800.0, 1600.0][i % 5]) for i in range(5)]
    m2 = compute_metrics(players2, "2026-08-01")
    assert list(m2["aggregate"]["dpi"]["categories"].keys()) == ["800", "1600", "400"]  # 1600/400 tie -> key asc


def test_scope_block_present():
    players = [p("steam:1", dpi=800.0)]
    m = compute_metrics(players, "2026-08-01", scope={"scope_id": "x", "tracked_teams": ["a"], "tracked_team_count": 1})
    assert m["aggregate"]["scope"]["scope_id"] == "x"


def test_public_aggregate_strips_per_player_values():
    players = [p("steam:1", dpi=800.0)]
    m = compute_metrics(players, "2026-08-01")
    pub = public_aggregate(m)
    assert "players" not in pub["panel"]
    assert pub["panel"]["player_ids"] == ["steam:1"]
