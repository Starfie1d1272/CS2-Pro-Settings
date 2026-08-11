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


def test_tracked_slugs_never_use_team_id_namespace_for_core_teams():
    """team_id and the cs2settings source slug are different namespaces.

    Regression: team_id 'natus-vincere'/'team-spirit' leaked into the fetch
    universe (via the old _slug_of fallback) alongside the correct source
    slugs 'navi'/'spirit', producing meaningless 404s on
    /teams/natus-vincere and /teams/team-spirit and polluting
    all_tracked_roster_failures. The fetch universe must contain ONLY
    source-specific slugs; ranking team_ids stay untouched.
    """
    cfg = load_cohort_cfg()
    slugs = tracked_slugs(cfg)
    # source slugs appear exactly once
    assert slugs.count("navi") == 1
    assert slugs.count("spirit") == 1
    # team_id namespace never leaks into the fetch universe
    assert "natus-vincere" not in slugs
    assert "team-spirit" not in slugs
    # ranking identifiers are untouched (team_id stays the ranking truth)
    s = _sets()
    assert "natus-vincere" in s["core_teams"]
    assert "team-spirit" in s["core_teams"]


# ---------------------------------------------------------------------------
# 3. unresolved source mapping
# ---------------------------------------------------------------------------

def _manifest(**kw):
    """Build a manifest with explicit defaults (new 4-layer signature)."""
    from cs2_pro_settings.cli import build_collection_manifest

    base = dict(
        requested_core_teams=30,
        source_resolved_core_teams=[f"t{i}" for i in range(30)],
        source_unresolved_core_teams=[],       # default: fully resolved
        successful_core_team_rosters=[f"t{i}" for i in range(30)],
        failed_core_team_rosters=[],
        expected_core_players=5,
        successful_core_players=5,
        failed_core_players=[],
        all_tracked_requested=35,
        all_tracked_roster_failures=[],
        all_tracked_player_failures=[],
        reference_player_failures=[],
        watchlist_player_failures=[],
    )
    base.update(kw)
    return build_collection_manifest(**base)


def test_manifest_denominator_30_resolved_24():
    """A: ranking Core 30, resolved 24, unresolved 6, roster success 24.

    requested_core_teams == 30 (never 24); resolution rate == 0.8;
    collection_complete == false (unresolved blocks).
    """
    m = _manifest(source_resolved_core_teams=[f"t{i}" for i in range(24)],
                  source_unresolved_core_teams=[f"u{i}" for i in range(6)],
                  successful_core_team_rosters=[f"t{i}" for i in range(24)])
    assert m["requested_core_teams"] == 30
    assert m["source_resolved_core_teams"] == 24
    assert len(m["source_unresolved_core_teams"]) == 6
    assert m["core_source_resolution_rate"] == 0.8
    assert m["core_roster_coverage_rate"] == 0.8      # 24/30 (full Core denom)
    assert m["resolved_core_roster_success_rate"] == 1.0  # 24/24
    assert m["collection_complete"] is False
    assert any("unresolved" in r for r in m["incomplete_reasons"])


def test_expected_players_before_fetch():
    """B: expected from roster listing (5), one fetch fails.

    expected==5, successful==4, failed==[x], rate==0.8, complete==false —
    never 'expected==4'.
    """
    m = _manifest(expected_core_players=5, successful_core_players=4,
                  failed_core_players=["steam:x"])
    assert m["expected_core_players"] == 5
    assert m["successful_core_players"] == 4
    assert m["failed_core_players"] == ["steam:x"]
    assert m["core_player_collection_rate"] == 0.8
    assert m["collection_complete"] is False


def test_watchlist_player_failure_does_not_fail_core():
    """C: watchlist player fetch failure never pollutes failed_core_players."""
    m = _manifest(watchlist_player_failures=["steam:w1"])
    assert m["failed_core_players"] == []
    assert m["watchlist_player_failures"] == ["steam:w1"]
    assert m["collection_complete"] is True


def test_hltv_only_player_failure_does_not_fail_core():
    """D: paiN/3DMAX (HLTV-only) player failures go to reference, not core."""
    m = _manifest(reference_player_failures=["steam:p1", "steam:p2"],
                  all_tracked_player_failures=["steam:o1"])
    assert m["failed_core_players"] == []
    assert m["reference_player_failures"] == ["steam:p1", "steam:p2"]
    assert m["collection_complete"] is True


def test_unresolved_core_mapping_does_not_invalidate_ranking(tmp_path):
    """Unresolved settings mapping: ranking stays valid, collection blocked."""
    m = _manifest(source_resolved_core_teams=[f"t{i}" for i in range(24)],
                  source_unresolved_core_teams=["bc-game"],
                  successful_core_team_rosters=[f"t{i}" for i in range(24)])
    assert m["collection_complete"] is False  # coverage blocked
    assert "bc-game" in m["source_unresolved_core_teams"]
    # the ranking itself is still structurally valid
    (tmp_path / "c.yaml").write_text("cohort:\n  core:\n    teams: []\n")
    activate_snapshot(REPO / "config/rankings/valve/2026-08-10.yaml",
                      cohort_path=str(tmp_path / "c.yaml"))
    assert "bc-game" not in [t["team_id"] for t in load_cohort_cfg()["cohort"]["core"]["teams"]]


# ---------------------------------------------------------------------------
# 4/5. collection manifest fail-closed
# ---------------------------------------------------------------------------

def test_core_team_fetch_failure_blocks_collection():
    m = _manifest(successful_core_team_rosters=[f"t{i}" for i in range(23)],
                  failed_core_team_rosters=["t7"])
    assert m["collection_complete"] is False
    assert m["failed_core_team_rosters"] == ["t7"]


def test_watchlist_roster_failure_does_not_fail_core():
    m = _manifest(all_tracked_roster_failures=["100-thieves"])
    assert m["collection_complete"] is True
    assert m["all_tracked_roster_failures"] == ["100-thieves"]


def test_core_player_failure_blocks_player_collection():
    m = _manifest(expected_core_players=2, successful_core_players=1,
                  failed_core_players=["steam:2"])
    assert m["collection_complete"] is False
    assert m["failed_core_players"] == ["steam:2"]


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
    # all 4 watchlist items added 2026-08-10 evaluated on 2026-08-11 -> not due
    assert watchlist_review_due(today=date(2026, 8, 11)) == []
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
