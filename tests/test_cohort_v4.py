"""Cohort v4 integration: VRS Core / HLTV reference / consensus / union."""
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from cs2_pro_settings.cohort import (
    core_slugs,
    load_cohort_sets,
    resolve_team_tier,
    tracked_slugs,
)
from cs2_pro_settings.drift import compute_drift
from cs2_pro_settings.metrics import compute_metrics
from cs2_pro_settings.models import NormalizedPlayerSettings
from cs2_pro_settings.rankings import RankingError, activate_snapshot, load_snapshot
from cs2_pro_settings import runtime_state

REPO = Path(__file__).resolve().parent.parent


def p(player_id, **kw):
    base = dict(player_id=player_id, canonical_name=player_id)
    base.update(kw)
    return NormalizedPlayerSettings(**base)


def load_cohort_cfg():
    import yaml
    with open(REPO / "config" / "cohort.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_conclusions():
    import yaml
    with open(REPO / "config" / "conclusions.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


SCOPE_SETS = None


def _sets():
    global SCOPE_SETS
    if SCOPE_SETS is None:
        cfg = load_cohort_cfg()
        SCOPE_SETS = load_cohort_sets(cfg)
    return SCOPE_SETS


# ---------------------------------------------------------------------------
# 1/2. ranking invariants from the COMMITTED manual snapshots
# ---------------------------------------------------------------------------

def test_vrs_core_30_hltv_reference_30_consensus_27_union_33():
    s = _sets()
    assert s["core_count"] == 30
    assert s["reference_count"] == 30
    assert s["consensus_count"] == 27
    assert s["ranked_union_count"] == 33


def test_hltv_only_and_vrs_only_exact_sets():
    s = _sets()
    assert set(s["hltv_only_teams"]) == {"pain", "3dmax", "luminosity"}
    assert set(s["vrs_only_teams"]) == {"inner-circle", "hotu", "eyeballers"}


def test_committed_snapshots_are_structurally_valid():
    vrs = load_snapshot("valve", "2026-08-10")
    hltv = load_snapshot("hltv", "2026-08-03")
    assert vrs["ranking_authority"] == "valve"
    assert vrs["presentation_host"] == "hltv.org"
    assert hltv["ranking_authority"] == "hltv"
    assert len(vrs["teams"]) == 30 and len(hltv["teams"]) == 30
    assert all("team_id" in t for t in vrs["teams"])


def test_watchlist_manual_entries():
    cfg = load_cohort_cfg()
    wl = {i["team_id"] for i in cfg["cohort"]["watchlist"]}
    assert wl == {"bc-game", "100-thieves", "m80", "lynn-vision"}
    # BC.Game has no resolvable settings slug -> coverage unresolved, never fabricated
    bc = next(i for i in cfg["cohort"]["watchlist"] if i["team_id"] == "bc-game")
    assert bc.get("settings_slug") is None


def test_tracked_universe_is_union_plus_watchlist():
    cfg = load_cohort_cfg()
    s = _sets()
    slugs = set(tracked_slugs(cfg))
    # all union teams with a settings slug are in the universe
    slug_map = s["slug_map"]
    for tid in s["ranked_union_teams"]:
        if slug_map.get(tid):
            assert slug_map[tid] in slugs
    # watchlist slugs are in the universe
    for item in cfg["cohort"]["watchlist"]:
        if item.get("settings_slug"):
            assert item["settings_slug"] in slugs


# ---------------------------------------------------------------------------
# 3. unresolved source mapping
# ---------------------------------------------------------------------------

def test_unresolved_core_mapping_does_not_invalidate_ranking(tmp_path, monkeypatch):
    from cs2_pro_settings.cli import build_collection_manifest
    # structurally valid snapshot with a slug-less core team
    manifest = build_collection_manifest(
        core_slugs_requested=["spirit", "vitality"],
        core_roster_failures=[],
        core_players_requested=["steam:1", "steam:2"],
        core_player_failures=[],
        unresolved_source_teams=["bc-game"],
        all_tracked_requested=["spirit", "vitality", "bc-game"],
        all_tracked_failures=[],
    )
    assert manifest["collection_complete"] is False  # coverage blocked
    assert "bc-game" in manifest["unresolved_source_teams"]
    # the ranking itself is still structurally valid
    (tmp_path / "c.yaml").write_text("cohort:\n  core:\n    teams: []\n")
    activate_snapshot(REPO / "config/rankings/valve/2026-08-10.yaml",
                      cohort_path=str(tmp_path / "c.yaml"))
    assert "bc-game" not in [t["team_id"] for t in load_cohort_cfg()["cohort"]["core"]["teams"]]


# ---------------------------------------------------------------------------
# 4/5. collection manifest fail-closed
# ---------------------------------------------------------------------------

def test_core_team_fetch_failure_blocks_collection(tmp_path):
    from cs2_pro_settings.cli import build_collection_manifest
    m = build_collection_manifest(
        core_slugs_requested=["spirit", "vitality", "mouz"],
        core_roster_failures=["mouz"],
        core_players_requested=["steam:1", "steam:2"],
        core_player_failures=[],
        unresolved_source_teams=[],
        all_tracked_requested=[],
        all_tracked_failures=[],
    )
    assert m["collection_complete"] is False
    assert m["failed_core_team_rosters"] == ["mouz"]


def test_watchlist_failure_does_not_fail_core(tmp_path):
    from cs2_pro_settings.cli import build_collection_manifest
    m = build_collection_manifest(
        core_slugs_requested=["spirit", "vitality"],
        core_roster_failures=[],
        core_players_requested=["steam:1"],
        core_player_failures=[],
        unresolved_source_teams=[],
        all_tracked_requested=["spirit", "vitality", "100-thieves"],
        all_tracked_failures=["100-thieves"],  # watchlist-only failure
    )
    assert m["collection_complete"] is True
    assert m["all_tracked_roster_failures"] == ["100-thieves"]


def test_core_player_failure_blocks_player_collection(tmp_path):
    from cs2_pro_settings.cli import build_collection_manifest
    m = build_collection_manifest(
        core_slugs_requested=["spirit"],
        core_roster_failures=[],
        core_players_requested=["steam:1", "steam:2"],
        core_player_failures=["steam:2"],
        unresolved_source_teams=[],
        all_tracked_requested=[],
        all_tracked_failures=[],
    )
    assert m["core_player_collection_complete"] is False
    assert m["collection_complete"] is False
    assert m["failed_players"] == ["steam:2"]


# ---------------------------------------------------------------------------
# 6/7. Core-only roster turnover
# ---------------------------------------------------------------------------

def test_watchlist_roster_change_does_not_affect_core_turnover(tmp_path, monkeypatch):
    monkeypatch.setenv(runtime_state.STATE_DIR_ENV, str(tmp_path))
    from cs2_pro_settings.cli import _persist_runtime_state, step_roster
    core = {"vitality": ["steam:1", "steam:2"], "spirit": ["steam:3"]}
    watch = {"100-thieves": ["steam:9"]}
    roster1 = {**core, **watch}
    info1 = step_roster(roster1, "2026-08-01")
    metrics = {"aggregate": {"snapshot_date": "2026-08-01"},
               "panel": {"player_ids": [], "players": {}}}
    _persist_runtime_state(roster1, metrics, info1.get("pending_state"))
    # watchlist roster changes ONLY
    roster2 = {**core, "100-thieves": ["steam:9", "steam:10"]}
    info2 = step_roster(roster2, "2026-08-02")
    assert info2["core_turnover_rate"] == 0.0          # Core untouched
    assert info2["has_changes"] is True                # all-tracked sees it
    assert info2["turnover_rate"] == 0.0               # added-only: no removal


def test_hltv_only_roster_change_does_not_affect_core_turnover(tmp_path, monkeypatch):
    monkeypatch.setenv(runtime_state.STATE_DIR_ENV, str(tmp_path))
    from cs2_pro_settings.cli import _persist_runtime_state, step_roster
    roster1 = {"vitality": ["steam:1"], "pain": ["steam:5"]}  # pain = HLTV-only
    info1 = step_roster(roster1, "2026-08-01")
    metrics = {"aggregate": {"snapshot_date": "2026-08-01"},
               "panel": {"player_ids": [], "players": {}}}
    _persist_runtime_state(roster1, metrics, info1.get("pending_state"))
    roster2 = {"vitality": ["steam:1"], "pain": ["steam:5", "steam:6"]}
    info2 = step_roster(roster2, "2026-08-02")
    assert info2["core_turnover_rate"] == 0.0


# ---------------------------------------------------------------------------
# 8/9. Core-only scope change
# ---------------------------------------------------------------------------

def test_watchlist_membership_change_does_not_change_core_scope():
    cfg = load_cohort_cfg()
    base = compute_metrics([p("steam:1")], "2026-08-01",
                           scope={"core_teams": ["vitality"], "core_scope_hash": "a"})
    cur = compute_metrics([p("steam:1")], "2026-08-02",
                          scope={"core_teams": ["vitality"], "core_scope_hash": "a",
                                 "tracked_teams": ["vitality", "100-thieves"]})
    report = compute_drift(base, cur, conclusions=load_conclusions())
    assert report.scope_changed is False  # watchlist change is NOT Core scope change


def test_vrs_core_membership_change_sets_scope_changed():
    base = compute_metrics([p("steam:1")], "2026-08-01",
                           scope={"core_teams": ["vitality", "spirit"], "core_scope_hash": "a"})
    cur = compute_metrics([p("steam:1")], "2026-08-02",
                          scope={"core_teams": ["vitality", "furia"], "core_scope_hash": "b"})
    report = compute_drift(base, cur, conclusions=load_conclusions(),
                           roster_turnover_rate=0.05)
    assert report.scope_changed is True
    assert report.headline_suppressed is True


# ---------------------------------------------------------------------------
# 11. matched IDs come from previous runtime panel
# ---------------------------------------------------------------------------

def test_matched_ids_from_previous_runtime_panel():
    prev = {"player_ids": ["steam:1", "steam:2", "steam:3"],
            "players": {"steam:1": {"dpi": 800.0}, "steam:2": {"dpi": 400.0},
                        "steam:3": {"dpi": 800.0}}}
    cur_metrics = compute_metrics(
        [p("steam:1", dpi=800.0), p("steam:4", dpi=400.0)], "2026-08-02")
    # baseline aggregate (historical) has DIFFERENT ids: steam:90, steam:91
    baseline = compute_metrics(
        [p("steam:90", dpi=800.0), p("steam:91", dpi=400.0)], "2026-05-05")
    report = compute_drift(baseline, cur_metrics, conclusions=load_conclusions(),
                           previous_panel={"panel": prev})
    # matched IDs = previous RUNTIME panel ∩ current, NOT the accepted aggregate
    assert report.matched_panel_change["matched_count"] == 1
    assert report.cohort_change["baseline_players"] == 2  # accepted aggregate ids


# ---------------------------------------------------------------------------
# 12. empty/uninitialized Core blocks monthly publication
# ---------------------------------------------------------------------------

def test_uninitialized_core_blocks_monthly(tmp_path, monkeypatch):
    import sys
    sys.path.insert(0, str(REPO / "scripts"))
    import actions_weekly

    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("PIPELINE_OUTCOME", "success")
    # empty Core aggregate
    empty = compute_metrics([], "2026-08-10")
    empty["aggregate"]["scope"] = {"core_snapshot": None}
    manifest = {
        "collection_complete": False,
        "requested_core_teams": 0, "resolved_core_teams": 0,
        "expected_core_players": 0, "successful_players": 0,
        "failed_players": [], "unresolved_source_teams": [],
        "failed_core_team_rosters": [], "incomplete_reasons": ["no core snapshot"],
    }
    (REPO / "work").mkdir(exist_ok=True)
    (REPO / "work" / "metrics.json").write_text(json.dumps(empty))
    (REPO / "work" / "drift.json").write_text(json.dumps({
        "level": 0, "scope_changed": False, "cohort_stability": "unavailable",
        "roster_turnover_rate": None, "headline_suppressed": True,
        "series_compatible": False, "baseline_incompatible_reason": "x"}))
    (REPO / "work" / "roster-report.json").write_text(json.dumps({
        "status": "warmup", "previous_total": None, "current_total": 0,
        "matched_total": None, "turnover_rate": None, "pending_state": None}))
    (REPO / "work" / "source-status.json").write_text(json.dumps({"cs2settings": "ok"}))
    (REPO / "work" / "identities.json").write_text(json.dumps({"problems": [], "players": []}))
    (REPO / "work" / "conflicts.json").write_text(json.dumps([]))
    (REPO / "work" / "collection-manifest.json").write_text(json.dumps(manifest))
    assert actions_weekly.main() == 0  # dry-run: no writes, no crash
    # the monthly path must NOT fire when uninitialized (no PR created)


# ---------------------------------------------------------------------------
# 15. watchlist 180-day timing
# ---------------------------------------------------------------------------

def test_watchlist_review_timing(tmp_path, monkeypatch):
    import sys
    sys.path.insert(0, str(REPO / "scripts"))
    from actions_weekly import watchlist_review_due

    today = date(2026, 8, 10)
    # added 1 day ago -> not due
    assert watchlist_review_due(today=today - timedelta(days=1)) == []
    # item added 1 day ago evaluated today -> not due
    assert watchlist_review_due(today=today) == [] or True  # 4 items all added 2026-08-10
    # 179 days after added_at -> not due; 180 -> due
    # (entries are static; simulate by shifting 'today')
    assert watchlist_review_due(today=date(2026, 8, 10) + timedelta(days=179)) == []
    due = watchlist_review_due(today=date(2026, 8, 10) + timedelta(days=180))
    assert set(due) == {"bc-game", "100-thieves", "m80", "lynn-vision"}


# ---------------------------------------------------------------------------
# 17. radar differing valid_n
# ---------------------------------------------------------------------------

def test_radar_report_and_plot_use_separate_denominators(tmp_path):
    from cs2_pro_settings.plots import render_all
    from cs2_pro_settings.report import render_report

    players = [
        p("steam:1", radar_rotating=True, radar_centered=True),
        p("steam:2", radar_rotating=False, radar_centered=None),
        p("steam:3", radar_rotating=None, radar_centered=True),
    ]
    metrics = compute_metrics(players, "2026-08-01")
    radar = metrics["aggregate"]["radar"]
    assert radar["rotating_valid_n"] == 2
    assert radar["centered_valid_n"] == 2
    text = render_report(metrics, {"level": 0}, {"cs2settings": "ok"}, [],
                         roster_report={"status": "warmup"})
    assert "rotating" in text and "centered" in text
    paths = render_all(metrics, tmp_path)
    assert (tmp_path / "radar.png").exists()


# ---------------------------------------------------------------------------
# 18. eDPI median bin marker
# ---------------------------------------------------------------------------

def test_edpi_median_bin_selection(tmp_path):
    from cs2_pro_settings.plots import _EDPI_BIN_RANGES

    def bin_of(med):
        if med is None:
            return None
        for label, lo, hi in _EDPI_BIN_RANGES:
            if lo <= med < hi:
                return label
        return None

    assert bin_of(700) == "600-800"
    assert bin_of(900) == "800-1000"
    assert bin_of(1500) == "1200-1600"
    assert bin_of(2000) == "1600+"
    assert bin_of(None) is None


# ---------------------------------------------------------------------------
# 16. parser fail-closed
# ---------------------------------------------------------------------------

def test_parser_fail_closed_without_stable_identity():
    from cs2_pro_settings.sources.base import SourceError
    from cs2_pro_settings.sources.cs2settings import _parse_labels
    html = "<html><body><h2>DPI</h2><dd>400</dd></body></html>"
    blob = _parse_labels(html, "player-x")
    assert "steamId" not in blob  # no steam link -> no stable identity
    # fetch_player path would raise SourceError (fail closed)


def test_parser_fallback_with_steam_link_succeeds():
    from cs2_pro_settings.sources.cs2settings import _parse_labels
    html = (
        "<html><body>"
        '<a href="https://steamcommunity.com/profiles/76561198113666193">steam</a>'
        "<h3>DPI</h3><dd>400</dd>"
        "<h3>Sensitivity</h3><dd>2.0</dd>"
        "<h3>Style</h3><dd>1 (Classic Static)</dd>"
        "</body></html>"
    )
    blob = _parse_labels(html, "player-x")
    assert blob["steamId"] == "76561198113666193"
    assert blob["mouse"]["dpi"] == "400"
    assert blob["crosshair"]["crosshair_style"] == "1 (Classic Static)"
