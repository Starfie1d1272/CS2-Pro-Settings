"""Source architecture: ranking/source separation, policies, ambiguity,
identity safety, completeness modes."""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from cs2_pro_settings.rankings import (  # noqa: E402
    RankingError,
    activate_snapshot,
    build_snapshot,
    load_mappings,
    resolve_team_source_ref,
)

MAPPINGS = load_mappings(str(REPO / "config" / "team-mappings.yaml"))


# ---------------------------------------------------------------------------
# A. source-specific team refs
# ---------------------------------------------------------------------------

def test_null_cs2_slug_does_not_mean_unobservable():
    # Luminosity has cs2settings.team_slug=null in the mapping
    assert resolve_team_source_ref("luminosity", "cs2settings", MAPPINGS) is None
    # but the team_id exists and the mapping entry is present (source refs
    # are per-source; prosettings/proconfig keys exist as empty refs)
    entry = next(e for e in MAPPINGS["teams"] if e["team_id"] == "luminosity")
    assert entry["team_id"] == "luminosity"
    assert "prosettings" in entry["source_refs"]
    assert "proconfig" in entry["source_refs"]


# ---------------------------------------------------------------------------
# B. ranking snapshot source independence
# ---------------------------------------------------------------------------

def test_ranking_snapshot_needs_only_rank_team_id(tmp_path):
    """A ranking entry with rank/team_id only (no settings_slug) activates."""
    import yaml

    # use real mapped display names so every entry resolves
    names = [e["display_names"][0] for e in MAPPINGS["teams"]][:30]
    snap = build_snapshot(
        list(enumerate(names, start=1)),
        "https://example.test/ranking", "2026-09-01",
        provider="valve", ranking_type="global", mappings=MAPPINGS)
    assert all("settings_slug" not in t for t in snap["teams"])
    (tmp_path / "c.yaml").write_text(
        "cohort:\n  core:\n    teams: []\n  reference:\n    teams: []\n")
    p = tmp_path / "snap.yaml"
    p.write_text(yaml.safe_dump(snap, sort_keys=False))
    activate_snapshot(p, cohort_path=str(tmp_path / "c.yaml"), target="core")
    out = yaml.safe_load((tmp_path / "c.yaml").read_text())
    assert out["cohort"]["core"]["teams"][0] == {"rank": 1, "team_id": "vitality"}


# ---------------------------------------------------------------------------
# C/D. scheduled vs local-review policy
# ---------------------------------------------------------------------------

def test_scheduled_policy_blocks_prosettings_even_with_capability(repo_root):
    import yaml

    cfg = yaml.safe_load((repo_root / "config" / "sources.yaml").read_text())
    ps = cfg["sources"]["prosettings"]
    assert ps["capabilities"]["player_settings"] is True
    assert ps["enabled_for_schedule"] is False  # capability != permission
    # scheduled source set must NOT include prosettings
    from cs2_pro_settings.cli import enabled_sources

    scheduled = {n for n, _ in enabled_sources(True)}
    assert "prosettings" not in scheduled
    assert "cs2settings" in scheduled
    local = {n for n, _ in enabled_sources(False)}
    assert "prosettings" in local  # user-triggered/local use allowed


# ---------------------------------------------------------------------------
# E. roster source != settings source
# ---------------------------------------------------------------------------

def test_roster_and_settings_sources_can_differ():
    """Conceptual: identity-safe observations combine a roster origin team
    with settings from another source (SteamID match). The canonical id is
    steam-based, so observations from different sources reconcile."""
    from cs2_pro_settings.identity import IdentityIndex

    idx = IdentityIndex()
    a = idx.register(source="cs2settings", source_id="zywoo", name="ZywOo",
                     team="vitality", steam_id="76561198113666193")
    b = idx.register(source="prosettings", source_id="zywoo", name="ZywOo",
                     steam_id="76561198113666193")
    assert a.player_id == b.player_id == "steam:76561198113666193"


# ---------------------------------------------------------------------------
# F. nickname-only merge is forbidden
# ---------------------------------------------------------------------------

def test_same_nickname_different_steam_never_merges():
    from cs2_pro_settings.identity import IdentityIndex

    idx = IdentityIndex()
    a = idx.register(source="cs2settings", source_id="donk", name="donk",
                     steam_id="11111111111111111")
    b = idx.register(source="prosettings", source_id="donk", name="donk",
                     steam_id="22222222222222222")
    assert a.player_id != b.player_id  # never merged by nickname
    assert a.player_id == "steam:11111111111111111"
    assert b.player_id == "steam:22222222222222222"


# ---------------------------------------------------------------------------
# I. alternate identity mismatch rejected
# ---------------------------------------------------------------------------

def test_lookup_slug_same_nickname_different_steam_rejected():
    """A proconfig/prosettings lookup candidate whose steam differs from the
    target must NOT merge (no auto-merge on nickname)."""
    from cs2_pro_settings.identity import IdentityIndex

    idx = IdentityIndex()
    target = idx.register(source="cs2settings", source_id="xantares",
                          name="XANTARES", steam_id="33333333333333333")
    candidate = idx.register(source="proconfig", source_id="xantares",
                             name="XANTARES", steam_id="44444444444444444")
    assert target.player_id != candidate.player_id


# ---------------------------------------------------------------------------
# J. duplicate roster membership
# ---------------------------------------------------------------------------

def test_duplicate_roster_membership_fails_scheduled(monkeypatch):
    from cs2_pro_settings import cli
    from cs2_pro_settings.sources.base import ParsedPlayer

    calls = {"roster_calls": []}

    class FakeSrc:
        name = "cs2settings"

        def list_team_roster(self, team_slug):
            calls["roster_calls"].append(team_slug)
            # same source_id appears on mouz AND gamerlegion (both Core)
            if team_slug == "mouz":
                return [{"source_id": "shared1", "name": "X", "role": "rifler"}]
            if team_slug == "gamerlegion":
                return [{"source_id": "shared1", "name": "X", "role": "rifler"}]
            return []

        def fetch_player(self, source_id):
            return ParsedPlayer(source="cs2settings", source_id=source_id,
                                name="X", source_url="f", retrieved_at="2026-08-11",
                                steam_id="55555555555555555", team=None, role="rifler",
                                fields={})

    monkeypatch.setattr(cli, "enabled_sources",
                        lambda scheduled_only: [("cs2settings", {})])
    monkeypatch.setattr(cli, "get_source", lambda name: FakeSrc())
    obs, roster, manifest = cli.step_collect(True, False, None, None)
    # ambiguous player assigned to NO team
    assert "shared1" not in {pid for v in roster.values() for pid in v}
    ambig = json.loads((cli.WORK / "roster-membership-ambiguities.json").read_text())
    assert ambig and ambig[0]["involves_core"] is True
    assert manifest["scheduled_collection_complete"] is False
    assert any("ambiguities" in r for r in manifest["incomplete_reasons"])


# ---------------------------------------------------------------------------
# K. role consistency (team page coach wins)
# ---------------------------------------------------------------------------

def test_team_page_coach_role_excludes_player(monkeypatch):
    from cs2_pro_settings import cli
    from cs2_pro_settings.sources.base import ParsedPlayer

    class FakeSrc:
        name = "cs2settings"

        def list_team_roster(self, team_slug):
            if team_slug == "vitality":
                return [{"source_id": "coach1", "name": "Coach", "role": "coach"}]
            return []

        def fetch_player(self, source_id):
            return ParsedPlayer(source="cs2settings", source_id=source_id,
                                name="Coach", source_url="f", retrieved_at="2026-08-11",
                                steam_id="66666666666666666", team=None, role=None,
                                fields={})

    monkeypatch.setattr(cli, "enabled_sources",
                        lambda scheduled_only: [("cs2settings", {})])
    monkeypatch.setattr(cli, "get_source", lambda name: FakeSrc())
    obs, roster, manifest = cli.step_collect(True, False, None, None)
    # effective_role = roster page role (coach) -> excluded at BOTH stages
    assert manifest["expected_core_players"] == 0
    assert obs == []


# ---------------------------------------------------------------------------
# L. daily issue body uses new manifest fields (no None)
# ---------------------------------------------------------------------------

def test_daily_incomplete_issue_body_new_fields(monkeypatch, tmp_path):
    import actions_common
    import actions_daily

    bodies = []

    def fake_sh(*args, check=True):
        if args[0] == "gh" and args[1] == "issue":
            bodies.append(args[-1])
        return ""

    monkeypatch.setattr(actions_common, "sh", fake_sh)
    monkeypatch.setattr(actions_common, "WORK", tmp_path)
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("PIPELINE_OUTCOME", "success")
    (tmp_path / "drift.json").write_text(json.dumps({"level": 0}))
    (tmp_path / "roster-report.json").write_text(json.dumps({"pending_state": None}))
    (tmp_path / "source-status.json").write_text(json.dumps({"cs2settings": "ok"}))
    (tmp_path / "metrics.json").write_text(json.dumps({"aggregate": {}, "panel": {}}))
    (tmp_path / "collection-manifest.json").write_text(json.dumps({
        "collection_complete": False,
        "scheduled_collection_complete": False,
        "requested_core_teams": 30,
        "source_resolved_core_teams": 24,
        "source_unresolved_core_teams": ["aurora", "big", "dendele", "hotu",
                                         "inner-circle", "magic"],
        "successful_core_team_rosters": 24,
        "failed_core_team_rosters": [],
        "expected_core_players": 112,
        "successful_core_players": 112,
        "failed_core_players": [],
        "incomplete_reasons": ["unresolved core source teams"],
    }))
    actions_daily.main()
    assert bodies, "issue body must be created"
    body = next((b for b in bodies if "requested core teams" in b), "")
    assert body, f"issue create body missing; got: {bodies[:2]}"
    assert "None" not in body
    assert "requested core teams: 30" in body
    assert "source unresolved: ['aurora'" in body
    assert "successful core players: 112" in body


# ---------------------------------------------------------------------------
# M. cmd_collect offline no KeyError
# ---------------------------------------------------------------------------

def test_cmd_collect_offline_no_keyerror(repo_root):
    from cs2_pro_settings import cli

    rc = cli.main(["collect", "--offline"])
    assert rc == 0


# ---------------------------------------------------------------------------
# N. legacy baseline count from aggregate
# ---------------------------------------------------------------------------

def test_legacy_baseline_count_uses_aggregate_player_count(repo_root):
    from cs2_pro_settings.drift import compute_drift
    from cs2_pro_settings.metrics import compute_metrics
    from cs2_pro_settings.models import NormalizedPlayerSettings

    def p(pid, **kw):
        base = dict(player_id=pid, canonical_name=pid)
        base.update(kw)
        return NormalizedPlayerSettings(**base)

    def load_conclusions():
        import yaml

        return yaml.safe_load((repo_root / "config" / "conclusions.yaml").read_text())

    legacy = compute_metrics([p(f"steam:{i}") for i in range(198)], "2026-05-05")
    legacy["panel"] = {"status": "unavailable", "player_ids": []}  # legacy: no ids
    cur = compute_metrics([p(f"steam:{i}") for i in range(198)], "2026-08-11")
    report = compute_drift(legacy, cur, conclusions=load_conclusions())
    assert report.cohort_change["baseline_players"] == 198  # NOT 0


# ---------------------------------------------------------------------------
# O. weekly series-incompatible missingness
# ---------------------------------------------------------------------------

def test_weekly_no_missingness_warning_across_series(monkeypatch, tmp_path):
    import actions_common
    import actions_weekly

    issues = []

    def fake_sh(*args, check=True):
        if args[0] == "gh" and args[1] == "issue":
            issues.append(args)
        return ""

    monkeypatch.setattr(actions_common, "sh", fake_sh)
    monkeypatch.setattr(actions_common, "WORK", tmp_path)
    monkeypatch.setattr(actions_common, "AGG", tmp_path / "agg")
    # actions_weekly binds AGG/ROOT at import time (from actions_common
    # import AGG) — patch the weekly module itself, not actions_common
    monkeypatch.setattr(actions_weekly, "AGG", tmp_path / "agg")
    monkeypatch.setattr(actions_weekly, "ROOT", REPO)
    monkeypatch.setattr(actions_common, "ROOT", REPO)
    # monthly candidate PR path must not touch the real repo in this test
    monkeypatch.setattr(actions_weekly, "create_or_update_candidate_pr",
                        lambda *a, **k: None)
    (tmp_path / "agg").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("PIPELINE_OUTCOME", "success")
    (tmp_path / "metrics.json").write_text(json.dumps({
        "aggregate": {"player_count": 100, "scope": {"core_snapshot": "2026-08-10"},
                      "series": {"series_id": "vrs-core-v2"},
                      "dpi": {"valid_n": 10}, "resolution": {"valid_n": 10},
                      "refresh_rate": {"valid_n": 10}, "fps_max": {"valid_n": 10}},
        "panel": {}}))
    (tmp_path / "drift.json").write_text(json.dumps({"level": 0}))
    (tmp_path / "roster-report.json").write_text(json.dumps({
        "core_turnover_rate": 0.0, "turnover_rate": 0.0, "pending_state": None}))
    (tmp_path / "source-status.json").write_text(json.dumps({"cs2settings": "ok"}))
    (tmp_path / "identities.json").write_text(json.dumps({"problems": [], "players": []}))
    (tmp_path / "conflicts.json").write_text(json.dumps([]))
    (tmp_path / "collection-manifest.json").write_text(json.dumps(
        {"collection_complete": True}))
    # legacy baseline (different series)
    (tmp_path / "agg" / "latest.json").write_text(json.dumps({
        "aggregate": {"player_count": 198, "series": {"series_id": "legacy-top30-plus-selected-v1"},
                      "dpi": {"valid_n": 198}, "resolution": {"valid_n": 198},
                      "refresh_rate": {"valid_n": 198}, "fps_max": {"valid_n": 198}}}))
    rc = actions_weekly.main()
    assert rc == 0
    # no missingness-spike quality issue across incompatible series
    assert not [c for c in issues if "missingness" in str(c)]


# ---------------------------------------------------------------------------
# Q. scheduled vs review completeness
# ---------------------------------------------------------------------------

def test_scheduled_vs_review_completeness_separate():
    from cs2_pro_settings.cli import build_collection_manifest

    def mk(**kw):
        base = dict(
            requested_core_teams=30,
            source_resolved_core_teams=[f"t{i}" for i in range(24)],
            source_unresolved_core_teams=[f"u{i}" for i in range(6)],
            successful_core_team_rosters=[f"t{i}" for i in range(24)],
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

    m = mk()
    assert m["scheduled_collection_complete"] is False  # unresolved blocks
    assert m["review_collection_complete"] is False      # no local roster either
    assert m["mode"] == "scheduled"
