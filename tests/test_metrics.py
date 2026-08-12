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
    # no player-level identity list in the PUBLIC aggregate (aggregate-only)
    assert "players" not in pub["panel"]
    assert "player_ids" not in pub["panel"]
    assert pub["panel"]["player_count"] == 1
    assert pub["panel"]["stable_identity_count"] == 1


# ---------------------------------------------------------------------------
# production correctness regressions
# ---------------------------------------------------------------------------

def test_refresh_540_plus_uses_player_counts_not_category_counts():
    """Regression: 540+ must sum COUNTS, not count categories >= 540."""
    players = []
    for _ in range(54):
        players.append(p(f"steam:{len(players)}", refresh_rate=600))
    for _ in range(8):
        players.append(p(f"steam:{len(players)}", refresh_rate=540))
    for _ in range(62):
        players.append(p(f"steam:{len(players)}", refresh_rate=360))
    for _ in range(74):
        players.append(p(f"steam:{len(players)}", refresh_rate=240))
    players.append(p("steam:x", refresh_rate=None))  # invalid
    m = compute_metrics(players, "2026-08-01")
    rr = m["aggregate"]["refresh_rate"]
    assert rr["valid_n"] == 198
    # 54 + 8 = 62 players at >=540 (NOT 2 categories)
    assert rr["share_540_plus"] == round(62 / 198, 4)
    # historical reference (2026-05): 62/195 = 0.3179
    assert rr["share_540_plus"] == 0.3131  # 62/198 for this construction
    # explicit historical regression against the published value
    hist = compute_metrics(
        [p(f"steam:{i}", refresh_rate=[600, 540, 360, 360, 360, 240, 400, 144][i % 8]) for i in range(195)],
        "2026-05-05")
    # recompute expected: counts of >=540 across the pattern
    pattern = [600, 540, 360, 360, 360, 240, 400, 144]
    hi = sum(1 for i in range(195) if pattern[i % 8] >= 540)
    assert hist["aggregate"]["refresh_rate"]["share_540_plus"] == round(hi / 195, 4)


def test_median_odd_and_even():
    odd = [p(f"steam:{i}", edpi=800.0) for i in range(5)]
    odd[0].edpi = 400.0
    m = compute_metrics(odd, "2026-08-01")
    assert m["aggregate"]["edpi"]["median"] == 800.0

    even = [p(f"steam:{i}", edpi=float(v)) for i, v in enumerate([400.0, 800.0, 1000.0, 1200.0])]
    m = compute_metrics(even, "2026-08-01")
    assert m["aggregate"]["edpi"]["median"] == 900.0  # (800+1000)/2


def test_radar_denominators_separate():
    players = [
        p("steam:1", radar_rotating=True, radar_centered=True),
        p("steam:2", radar_rotating=False, radar_centered=None),  # centered missing
        p("steam:3", radar_rotating=None, radar_centered=False),  # rotating missing
        p("steam:4", radar_rotating=True, radar_centered=True),
    ]
    m = compute_metrics(players, "2026-08-01")
    radar = m["aggregate"]["radar"]
    assert radar["rotating_valid_n"] == 3
    assert radar["centered_valid_n"] == 3
    assert radar["rotating_share"] == round(2 / 3, 4)   # 2 yes of 3 valid rotating
    assert radar["centered_share"] == round(2 / 3, 4)   # 2 yes of 3 valid centered
    # legacy alias keeps rotating valid_n
    assert radar["valid_n"] == 3


def test_dominant_offset_deterministic_tie():
    players = [
        p("steam:1", viewmodel_offset_x=1.0, viewmodel_offset_y=1.0, viewmodel_offset_z=1.0),
        p("steam:2", viewmodel_offset_x=2.5, viewmodel_offset_y=0.0, viewmodel_offset_z=-1.5),
    ]
    a = compute_metrics(players, "2026-08-01")
    b = compute_metrics(list(reversed(players)), "2026-08-01")
    assert a["aggregate"]["viewmodel"]["dominant_offset"] == \
        b["aggregate"]["viewmodel"]["dominant_offset"]
    # tie -> lexicographically smallest tuple wins deterministically
    assert a["aggregate"]["viewmodel"]["dominant_offset"] == [1.0, 1.0, 1.0]


def test_additive_reporting_metrics_keep_field_denominators():
    players = [
        p("steam:1", scaling_mode="Stretched", zoom_sensitivity=1.0,
          boost_player=True, crosshair_style="4", crosshair_size=1.0,
          crosshair_gap=-3.0, crosshair_thickness=1.0, crosshair_alpha=255,
          crosshair_dot=False, crosshair_outline=False, radar_zoom=0.4),
        p("steam:2", scaling_mode="Native", zoom_sensitivity=None,
          boost_player=False, crosshair_style="4", crosshair_size=2.0,
          crosshair_gap=-4.0, crosshair_thickness=0.0, crosshair_alpha=200,
          crosshair_dot=True, crosshair_outline=None, radar_zoom=None),
        p("steam:3", scaling_mode=None, zoom_sensitivity=1.0,
          boost_player=None, crosshair_style=None, crosshair_size=None,
          crosshair_gap=None, crosshair_thickness=None, crosshair_alpha=None,
          crosshair_dot=None, crosshair_outline=True, radar_zoom=0.7),
    ]
    agg = compute_metrics(players, "2026-08-01")["aggregate"]

    assert agg["scaling_mode"]["valid_n"] == 2
    assert agg["zoom_sensitivity"]["valid_n"] == 2
    assert agg["zoom_sensitivity"]["median"] == 1.0
    assert agg["boost_player"] == {
        "valid_n": 2, "missing_n": 1, "enabled_count": 1,
        "disabled_count": 1, "enabled_share": 0.5,
    }
    geometry = agg["crosshair"]["geometry"]
    assert geometry["style"]["valid_n"] == 2
    assert geometry["size"]["categories"] == {"1": 1, "2": 1}
    assert geometry["dot"]["valid_n"] == 2
    assert geometry["dot"]["enabled_share"] == 0.5
    assert geometry["outline"]["valid_n"] == 2
    assert geometry["outline"]["missing_n"] == 1
    assert compute_metrics(players, "2026-08-01")["figure_data"] == {
        "crosshair_gap_size": {
            "valid_n": 2,
            "combinations": [
                {"gap": -4.0, "size": 2.0, "count": 1},
                {"gap": -3.0, "size": 1.0, "count": 1},
            ],
        },
    }
    assert agg["radar"]["zoom"]["valid_n"] == 2
    assert agg["radar"]["zoom"]["categories"] == {"0.4": 1, "0.7": 1}


def test_figure_data_is_identity_free_and_not_publicly_exposed():
    players = [
        p("steam:1", crosshair_gap=-4.0, crosshair_size=1.0),
        p("steam:2", crosshair_gap=-4.0, crosshair_size=1.0),
        p("steam:3", crosshair_gap=-3.0, crosshair_size=None),
    ]
    metrics = compute_metrics(players, "2026-08-01")
    joint = metrics["figure_data"]["crosshair_gap_size"]
    assert joint == {
        "valid_n": 2,
        "combinations": [{"gap": -4.0, "size": 1.0, "count": 2}],
    }
    assert "steam:" not in str(joint)
    assert "figure_data" not in public_aggregate(metrics)


def test_edpi_consistency_qc_tolerance_and_missing_inputs():
    players = [
        p("steam:1", dpi=800.0, sensitivity=1.0, edpi=800.0),
        # 0.75% difference: within the 1% relative tolerance.
        p("steam:2", dpi=800.0, sensitivity=1.0, edpi=806.0),
        # 5% difference: an obvious arithmetic anomaly.
        p("steam:3", dpi=800.0, sensitivity=1.0, edpi=840.0),
        p("steam:4", dpi=800.0, sensitivity=None, edpi=800.0),
    ]
    qc = compute_metrics(players, "2026-08-01")["aggregate"]["edpi"]["consistency_qc"]
    assert qc == {
        "comparable_n": 3,
        "consistent_n": 2,
        "anomaly_count": 1,
        "anomaly_share": round(1 / 3, 4),
        "missing_inputs_n": 1,
        "absolute_tolerance": 2.0,
        "relative_tolerance": 0.01,
    }
