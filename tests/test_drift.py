"""Drift: Level 0/1/2, thresholds, matched panel, scope-change protection."""
import json
from copy import deepcopy

from cs2_pro_settings.drift import compute_drift
from cs2_pro_settings.metrics import compute_metrics
from cs2_pro_settings.models import NormalizedPlayerSettings

SCOPE_V1 = {"scope_id": "top-tier-plus-selected-v1", "tracked_teams": [], "tracked_team_count": 41}
SCOPE_V2 = {"scope_id": "top-tier-plus-selected-v1", "tracked_teams": ["vitality"], "tracked_team_count": 30}


def p(player_id, **kw):
    base = dict(player_id=player_id, canonical_name=player_id)
    base.update(kw)
    return NormalizedPlayerSettings(**base)


def metrics_for(players, date, scope):
    return compute_metrics(players, date, scope=scope)


def load_conclusions(repo_root):
    import yaml
    with open(repo_root / "config" / "conclusions.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def mk_cohort_800_dominant(n=198, scope=SCOPE_V1):
    players = []
    for i in range(n):
        dpi = 800.0 if i < 106 else (400.0 if i < 188 else 1600.0)
        players.append(p(f"steam:{i}", dpi=dpi, edpi=800.0))
    return players


def test_baseline_equals_baseline_level_0(repo_root):
    baseline = metrics_for(mk_cohort_800_dominant(), "2026-05-05", SCOPE_V1)
    current = metrics_for(mk_cohort_800_dominant(), "2026-05-05", SCOPE_V1)
    report = compute_drift(baseline, current, conclusions=load_conclusions(repo_root))
    assert report.level == 0
    assert report.changed_metrics == []


def test_5pp_share_change_level_1(repo_root):
    baseline = metrics_for(mk_cohort_800_dominant(), "2026-05-05", SCOPE_V1)
    # move 10 players from 800 -> 400: 800 share 106/198=53.5% -> 96/198=48.5%
    # (5.05pp, 800 stays dominant at 96 vs 92)
    players = mk_cohort_800_dominant()
    for i in range(10):
        players[i].dpi = 400.0
    current = metrics_for(players, "2026-08-01", SCOPE_V1)
    report = compute_drift(baseline, current, conclusions=load_conclusions(repo_root))
    assert report.level == 1
    dpi_share = next(c for c in report.changed_metrics if c["conclusion"] == "dpi_800_share")
    assert dpi_share["level"] == 1


def test_small_change_level_0(repo_root):
    baseline = metrics_for(mk_cohort_800_dominant(), "2026-05-05", SCOPE_V1)
    players = mk_cohort_800_dominant()
    for i in range(3):  # 1.5pp only
        players[i].dpi = 400.0
    current = metrics_for(players, "2026-08-01", SCOPE_V1)
    report = compute_drift(baseline, current, conclusions=load_conclusions(repo_root))
    assert report.level == 0


def test_dominant_flip_level_2(repo_root):
    baseline = metrics_for(mk_cohort_800_dominant(), "2026-05-05", SCOPE_V1)
    # flip: 400 becomes dominant
    players = mk_cohort_800_dominant()
    for i in range(198):
        players[i].dpi = 400.0 if i < 120 else 800.0
    current = metrics_for(players, "2026-08-01", SCOPE_V1)
    report = compute_drift(baseline, current, conclusions=load_conclusions(repo_root))
    assert report.level == 2
    dom = next(c for c in report.changed_metrics if c["conclusion"] == "dpi_dominant")
    assert dom["level"] == 2
    assert dom["baseline"] == "800"
    assert dom["current"] == "400"


def test_scope_changed_caps_level_2(repo_root):
    baseline = metrics_for(mk_cohort_800_dominant(scope=SCOPE_V1), "2026-05-05", SCOPE_V1)
    # dominant flip, but tracked-team scope changed (legacy 41 -> v2 30)
    players = mk_cohort_800_dominant(scope=SCOPE_V2)
    for i in range(198):
        players[i].dpi = 400.0 if i < 120 else 800.0
    current = metrics_for(players, "2026-08-01", SCOPE_V2)
    report = compute_drift(baseline, current, conclusions=load_conclusions(repo_root))
    assert report.scope_changed is True
    assert report.level <= 1  # NOT judged as Level 2
    assert report.scope_warning != ""


def test_matched_panel_separates_roster_change(repo_root):
    baseline_players = [p(f"steam:{i}", dpi=800.0) for i in range(100)]
    baseline = metrics_for(baseline_players, "2026-05-05", SCOPE_V2)
    # 10 removed, 10 added, 90 matched with changed dpi
    current_players = [p(f"steam:{i}", dpi=400.0) for i in range(10, 110)]
    current = metrics_for(current_players, "2026-08-01", SCOPE_V2)
    report = compute_drift(baseline, current, conclusions=load_conclusions(repo_root),
                           previous_panel=baseline)
    assert report.cohort_change["removed"] == [f"steam:{i}" for i in range(10)]
    assert report.cohort_change["added"] == [f"steam:{i}" for i in range(100, 110)]
    assert report.matched_panel_change["matched_count"] == 90
    assert report.matched_panel_change["status"] == "available"
    # per-field matched change computed on the intersection only
    assert report.matched_panel_change["per_field"]["dpi"]["compared"] == 90


def test_matched_panel_unavailable_without_stable_ids(repo_root):
    # legacy-style baseline: no stable player IDs -> matched panel unavailable
    baseline_players = mk_cohort_800_dominant(scope=SCOPE_V1)
    baseline = metrics_for(baseline_players, "2026-05-05", SCOPE_V1)
    baseline["panel"] = {"status": "unavailable", "player_ids": []}
    current = metrics_for(mk_cohort_800_dominant(scope=SCOPE_V2), "2026-08-01", SCOPE_V2)
    report = compute_drift(baseline, current, conclusions=load_conclusions(repo_root))
    assert report.matched_panel_change["status"] == "unavailable"


def test_drift_report_json_serializable(repo_root):
    baseline = metrics_for(mk_cohort_800_dominant(), "2026-05-05", SCOPE_V1)
    current = metrics_for(mk_cohort_800_dominant(), "2026-08-01", SCOPE_V1)
    report = compute_drift(baseline, current, conclusions=load_conclusions(repo_root))
    json.dumps(report.__dict__)
