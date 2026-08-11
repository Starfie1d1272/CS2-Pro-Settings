"""Cohort preservation: zero-observation stable identities survive
reconciliation and metrics; settings availability is separate from cohort
membership; public aggregates never leak identities."""
from cs2_pro_settings.identity import IdentityIndex
from cs2_pro_settings.metrics import compute_metrics, public_aggregate
from cs2_pro_settings.models import NormalizedPlayerSettings, SourceObservation
from cs2_pro_settings.reconcile import reconcile
from cs2_pro_settings.runtime_state import compare_panels


def _ids(*steams):
    idx = IdentityIndex()
    for i, s in enumerate(steams):
        idx.register(source="cs2settings", source_id=f"p{i}", name=f"P{i}",
                     team="vitality", steam_id=s)
    return {p.player_id: p for p in idx.all()}


def _obs(player_id, field, value):
    return SourceObservation(player_id=player_id, field=field, value=value,
                             source="cs2settings", source_url="u",
                             retrieved_at="2026-08-11")


# ---------------------------------------------------------------------------
# R1/R2/R4 reconcile
# ---------------------------------------------------------------------------

def test_zero_observation_identity_preserved():
    ids = _ids("11111111111111111", "22222222222222222")
    a, b = sorted(ids)
    res = reconcile([_obs(a, "dpi", "800")], {"dpi": ["cs2settings"]},
                    {"cs2settings"}, ids)
    assert set(res.players) == {a, b}
    assert res.players[a].dpi == "800"  # raw value; typing happens upstream
    assert res.players[b].dpi is None
    assert res.players[b].provenance == {}


def test_identity_metadata_preserved_for_zero_setting_player():
    ids = _ids("11111111111111111", "22222222222222222")
    a, b = sorted(ids)
    res = reconcile([_obs(a, "dpi", "800")], {"dpi": ["cs2settings"]},
                    {"cs2settings"}, ids)
    assert res.players[b].canonical_name == "P1"
    assert res.players[b].team == "vitality"


def test_conflicts_unchanged_with_preserved_universe():
    ids = _ids("11111111111111111", "22222222222222222")
    a, b = sorted(ids)
    obs = [
        _obs(a, "dpi", "800"),
        SourceObservation(player_id=a, field="dpi", value="400",
                          source="prosettings", source_url="u2",
                          retrieved_at="2026-08-11"),
    ]
    res = reconcile(obs, {"dpi": ["cs2settings", "prosettings"]},
                    {"cs2settings", "prosettings"}, ids)
    assert set(res.players) == {a, b}
    assert len(res.conflicts) >= 1  # 800 vs 400 disagreement still recorded
    assert res.players[a].dpi in ("400", "800")


def test_no_identities_fallback_is_observation_driven():
    a = "steam:11111111111111111"
    res = reconcile([_obs(a, "DPI", "800")], {"dpi": ["cs2settings"]},
                    {"cs2settings"}, None)
    assert set(res.players) == {a}


# ---------------------------------------------------------------------------
# metrics: cohort vs availability
# ---------------------------------------------------------------------------

def _np(pid, **kw):
    base = dict(player_id=pid, canonical_name=pid, team="vitality")
    base.update(kw)
    return NormalizedPlayerSettings(**base)


def _three_player_metrics():
    return compute_metrics([
        _np("steam:1", dpi=800.0, resolution="1280x960"),
        _np("steam:2", dpi=400.0),
        _np("steam:3"),
    ], "2026-08-11")


def test_player_count_includes_zero_setting_members():
    m = _three_player_metrics()
    assert m["aggregate"]["player_count"] == 3
    assert len(m["panel"]["player_ids"]) == 3  # panel universe == cohort


def test_public_panel_counts_full_cohort():
    m = _three_player_metrics()
    pub = public_aggregate(m)
    assert pub["panel"]["player_count"] == 3
    assert pub["panel"]["stable_identity_count"] == 3


def test_field_valid_n_excludes_missing():
    m = _three_player_metrics()
    assert m["aggregate"]["dpi"]["valid_n"] == 2
    assert m["aggregate"]["resolution"]["valid_n"] == 1
    assert m["aggregate"]["fps_max"]["valid_n"] == 0


def test_settings_availability_aggregate():
    m = _three_player_metrics()
    av = m["aggregate"]["settings_availability"]
    assert av == {"cohort_players": 3, "players_with_any_setting": 2,
                  "players_with_zero_settings": 1, "any_setting_share": 0.6667}


def test_public_aggregate_leaks_no_identities():
    m = _three_player_metrics()
    pub = public_aggregate(m)
    assert "player_ids" not in pub.get("panel", {})
    assert "players" not in pub.get("panel", {})
    av = pub["aggregate"]["settings_availability"]
    assert av["cohort_players"] == 3 and av["players_with_zero_settings"] == 1


# ---------------------------------------------------------------------------
# matched panel: previously empty player gets a value -> missing_to_value
# ---------------------------------------------------------------------------

def test_matched_panel_missing_to_value_for_previously_empty_player():
    prev = {"player_ids": ["steam:1", "steam:2"],
            "players": {"steam:1": {"dpi": 800.0}, "steam:2": {"dpi": None}}}
    cur = {"player_ids": ["steam:1", "steam:2"],
           "players": {"steam:1": {"dpi": 800.0}, "steam:2": {"dpi": 800.0}}}
    res = compare_panels(prev, cur)
    assert res["matched_count"] == 2  # B stays matched, not a new member
    dpi = res["per_field"]["dpi"]
    assert dpi["compared"] == 1
    assert dpi["changed"] == 0
    assert dpi["missing_to_value"] == 1
    assert dpi["value_to_missing"] == 0
    assert dpi["missing_transition"] == 1
