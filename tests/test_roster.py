"""Roster drift: diffs, confirmation window, turnover, stability guard."""
from cs2_pro_settings.drift import compute_drift
from cs2_pro_settings.metrics import compute_metrics
from cs2_pro_settings.models import NormalizedPlayerSettings
from cs2_pro_settings.roster import (
    compute_roster_report,
    roster_stability,
    update_pending_state,
)

SCOPE = {"scope_id": "top-tier-plus-selected-v1", "tracked_teams": ["vitality"], "tracked_team_count": 30}


def p(player_id, **kw):
    base = dict(player_id=player_id, canonical_name=player_id)
    base.update(kw)
    return NormalizedPlayerSettings(**base)


def load_conclusions(repo_root):
    import yaml
    with open(repo_root / "config" / "conclusions.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# roster diff
# ---------------------------------------------------------------------------

def test_same_roster_no_drift():
    prev = {"vitality": ["steam:1", "steam:2", "steam:3"]}
    cur = {"vitality": ["steam:1", "steam:2", "steam:3"]}
    report = compute_roster_report("2026-08-01", prev, cur)
    assert report.has_changes is False
    assert report.team_drifts == []
    assert report.turnover_rate == 0.0


def test_one_out_one_in_correct_diff():
    prev = {"vitality": ["steam:1", "steam:2", "steam:3"]}
    cur = {"vitality": ["steam:1", "steam:2", "steam:4"]}
    report = compute_roster_report("2026-08-01", prev, cur)
    assert report.has_changes is True
    d = report.team_drifts[0]
    assert d.removed_players == ["steam:3"]
    assert d.added_players == ["steam:4"]
    assert d.unchanged_players == ["steam:1", "steam:2"]
    assert report.matched_total == 2
    assert report.turnover_rate == round(1 - 2 / 3, 4)


def test_new_team_appears():
    prev = {"vitality": ["steam:1"]}
    cur = {"vitality": ["steam:1"], "falcons": ["steam:9"]}
    report = compute_roster_report("2026-08-01", prev, cur)
    assert report.has_changes is True
    d = report.team_drifts[0]
    assert d.team_id == "falcons"
    assert d.added_players == ["steam:9"]


# ---------------------------------------------------------------------------
# confirmation window
# ---------------------------------------------------------------------------

def test_first_observation_pending_no_notification():
    prev = {"vitality": ["steam:1"]}
    cur = {"vitality": ["steam:1", "steam:2"]}
    report = compute_roster_report("2026-08-01", prev, cur)
    state = update_pending_state(None, report, "2026-08-01")
    assert state is not None
    assert state["status"] == "pending"
    assert state["fingerprint"] == report.fingerprint()


def test_second_identical_observation_confirmed():
    prev = {"vitality": ["steam:1"]}
    cur = {"vitality": ["steam:1", "steam:2"]}
    r1 = compute_roster_report("2026-08-01", prev, cur)
    pending = update_pending_state(None, r1, "2026-08-01")
    r2 = compute_roster_report("2026-08-02", prev, cur)
    state = update_pending_state(pending, r2, "2026-08-02")
    assert state is not None
    assert state["status"] == "confirmed"
    assert state["first_observed_at"] == "2026-08-01"


def test_pending_change_disappears_cleared():
    prev = {"vitality": ["steam:1"]}
    cur = {"vitality": ["steam:1", "steam:2"]}
    r1 = compute_roster_report("2026-08-01", prev, cur)
    pending = update_pending_state(None, r1, "2026-08-01")
    # next run: roster back to previous
    r2 = compute_roster_report("2026-08-02", prev, prev)
    state = update_pending_state(pending, r2, "2026-08-02")
    assert state is None  # cleared


def test_different_fingerprint_restarts_window():
    prev = {"vitality": ["steam:1"]}
    cur_a = {"vitality": ["steam:1", "steam:2"]}
    cur_b = {"vitality": ["steam:1", "steam:3"]}
    r1 = compute_roster_report("2026-08-01", prev, cur_a)
    pending = update_pending_state(None, r1, "2026-08-01")
    r2 = compute_roster_report("2026-08-02", prev, cur_b)
    state = update_pending_state(pending, r2, "2026-08-02")
    assert state is not None
    assert state["status"] == "pending"  # not confirmed, window restarted
    assert state["fingerprint"] == r2.fingerprint()


# ---------------------------------------------------------------------------
# turnover / stability
# ---------------------------------------------------------------------------

def test_turnover_10_percent_stable():
    prev = {"vitality": [f"steam:{i}" for i in range(10)]}
    cur = {"vitality": [f"steam:{i}" for i in range(9)]}  # 1/10 out
    report = compute_roster_report("2026-08-01", prev, cur)
    assert report.turnover_rate == 0.1
    assert roster_stability(report.turnover_rate, 0.15) == "stable"


def test_turnover_20_percent_unstable():
    prev = {"vitality": [f"steam:{i}" for i in range(10)]}
    cur = {"vitality": [f"steam:{i}" for i in range(8)]}  # 2/10 out
    report = compute_roster_report("2026-08-01", prev, cur)
    assert report.turnover_rate == 0.2
    assert roster_stability(report.turnover_rate, 0.15) == "unstable"


def test_turnover_unavailable_on_empty_previous():
    report = compute_roster_report("2026-08-01", {}, {"vitality": ["steam:1"]})
    assert report.turnover_rate is None
    assert roster_stability(None, 0.15) == "unavailable"


# ---------------------------------------------------------------------------
# drift integration: suppression
# ---------------------------------------------------------------------------

def mk_players(dpi_800_first=106):
    players = []
    for i in range(198):
        dpi = 800.0 if i < dpi_800_first else (400.0 if i < 188 else 1600.0)
        players.append(p(f"steam:{i}", dpi=dpi, edpi=800.0))
    return players


def test_roster_unstable_plus_dominant_flip_suppressed(repo_root):
    baseline = compute_metrics(mk_players(), "2026-05-05", scope=SCOPE)
    flipped = mk_players(dpi_800_first=80)  # 400 dominant
    current = compute_metrics(flipped, "2026-08-01", scope=SCOPE)
    report = compute_drift(baseline, current, conclusions=load_conclusions(repo_root),
                           roster_turnover_rate=0.2)
    assert report.headline_suppressed is True
    assert report.cohort_stability == "unstable"
    assert report.level <= 1  # overall flip NOT judged as Level 2
    assert "roster turnover" in report.suppression_reason


def test_roster_stable_plus_dominant_flip_level_2(repo_root):
    baseline = compute_metrics(mk_players(), "2026-05-05", scope=SCOPE)
    flipped = mk_players(dpi_800_first=80)
    current = compute_metrics(flipped, "2026-08-01", scope=SCOPE)
    report = compute_drift(baseline, current, conclusions=load_conclusions(repo_root),
                           roster_turnover_rate=0.05)
    assert report.headline_suppressed is False
    assert report.cohort_stability == "stable"
    assert report.level == 2


def test_roster_unstable_matched_panel_unchanged_warning(repo_root):
    baseline_players = mk_players()
    baseline = compute_metrics(baseline_players, "2026-05-05", scope=SCOPE)
    # same players, one leaves and one enters (composition-only change)
    current_players = mk_players()
    current_players[0] = p("steam:999", dpi=400.0, edpi=800.0)  # roster composition change
    current = compute_metrics(current_players, "2026-08-01", scope=SCOPE)
    report = compute_drift(baseline, current, conclusions=load_conclusions(repo_root),
                           roster_turnover_rate=0.2, previous_panel=baseline)
    assert report.headline_suppressed is True
    # matched panel exists and is compared independently
    assert report.matched_panel_change["matched_count"] == 197
    assert report.matched_panel_change["per_field"]["dpi"]["changed"] == 0


def test_roster_unstable_matched_panel_material_change_reported_separately(repo_root):
    """F: overall unstable but the matched panel itself materially changed."""
    baseline_players = mk_players()
    baseline = compute_metrics(baseline_players, "2026-05-05", scope=SCOPE)
    # matched players (steam:0..197 minus a few) change dpi en masse; a few
    # leave and a few enter to make the roster unstable
    current_players = mk_players(dpi_800_first=60)  # big same-player shift
    current_players[0] = p("steam:999", dpi=400.0, edpi=800.0)
    current_players[1] = p("steam:998", dpi=400.0, edpi=800.0)
    current = compute_metrics(current_players, "2026-08-01", scope=SCOPE)
    report = compute_drift(baseline, current, conclusions=load_conclusions(repo_root),
                           roster_turnover_rate=0.2, previous_panel=baseline)
    # overall headline suppressed due to roster instability
    assert report.headline_suppressed is True
    assert report.level <= 1
    # matched panel still computed independently and shows material change
    mp = report.matched_panel_change
    assert mp["matched_count"] == 196
    assert mp["per_field"]["dpi"]["changed"] == 46  # steam:60..105 shifted 800->400
    assert mp["per_field"]["dpi"]["compared"] == 196


def test_scope_and_roster_states_independent(repo_root):
    baseline = compute_metrics(mk_players(), "2026-05-05", scope=SCOPE)
    other_scope = dict(SCOPE, tracked_teams=["vitality", "falcons"], tracked_team_count=31)
    current = compute_metrics(mk_players(), "2026-08-01", scope=other_scope)
    report = compute_drift(baseline, current, conclusions=load_conclusions(repo_root),
                           roster_turnover_rate=0.2)
    assert report.scope_changed is True
    assert report.cohort_stability == "unstable"
    assert report.headline_suppressed is True
    # suppression reason reflects scope first (scope > roster in priority)
    assert "scope" in report.suppression_reason
