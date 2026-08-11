"""Final correctness repair regressions (round: manifest / roster origin /
activation targets / weekly semantics / missing-manifest fail-closed)."""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import actions_common  # noqa: E402
import actions_daily  # noqa: E402
import actions_weekly  # noqa: E402


def _mk_src(rosters: dict, players: dict):
    """In-memory roster/player source mimicking CS2SettingsSource shape."""
    from cs2_pro_settings.sources.base import ParsedPlayer, SourceError

    class FakeSrc:
        name = "cs2settings"

        def list_team_roster(self, team_slug: str) -> list[dict]:
            if team_slug not in rosters:
                raise SourceError(f"no roster for {team_slug}")
            return [dict(e, roster_team_slug=team_slug) for e in rosters[team_slug]]

        def fetch_player(self, source_id: str) -> ParsedPlayer:
            if source_id not in players:
                raise SourceError(f"no player {source_id}")
            return players[source_id]

    return FakeSrc()


# ---------------------------------------------------------------------------
# E. empty roster parser fails closed (real parser, no network)
# ---------------------------------------------------------------------------

def test_empty_roster_parser_raises_source_error(monkeypatch):
    from cs2_pro_settings.sources.base import SourceError
    from cs2_pro_settings.sources.cs2settings import CS2SettingsSource

    src = CS2SettingsSource()
    monkeypatch.setattr(src, "_get_text",
                        lambda url: "<html><body>no roster links here</body></html>")
    with pytest.raises(SourceError):
        src.list_team_roster("g2")


# ---------------------------------------------------------------------------
# F. team page origin is membership evidence; player-page team is a check
# ---------------------------------------------------------------------------

def test_team_page_origin_wins_over_player_page_team(monkeypatch, tmp_path):
    from cs2_pro_settings import cli
    from cs2_pro_settings.sources.base import ParsedPlayer

    monkeypatch.setattr(cli, "enabled_sources", lambda scheduled_only: [("cs2settings", {})])
    src = _mk_src(
        rosters={"g2": [{"source_id": "g2player1", "name": "P1", "role": "rifler"}]},
        players={"g2player1": ParsedPlayer(
            source="cs2settings", source_id="g2player1", name="P1",
            source_url="fixture://g2player1", retrieved_at="2026-08-11",
            steam_id="76561198000000001", team="old-team", role="rifler",
            country="DE", fields={"dpi": 400})},
    )
    monkeypatch.setattr(cli, "get_source", lambda name: src)
    obs, roster, manifest = cli.step_collect(True, False, None, None)
    # membership keyed by TEAM PAGE origin (g2) via the stable player_id
    assert "steam:76561198000000001" in roster["g2"]
    # conflict recorded, not silently overwritten
    conflicts = json.loads((cli.WORK / "team-membership-conflicts.json").read_text())
    assert conflicts and conflicts[0]["roster_team_slug"] == "g2"
    assert conflicts[0]["player_page_team"] == "old-team"


def test_semantic_fallback_without_player_page_team_stays_in_core(monkeypatch, tmp_path):
    """G: parsed.team=None (fallback) but roster origin = vitality -> Core."""
    from cs2_pro_settings import cli
    from cs2_pro_settings.sources.base import ParsedPlayer

    monkeypatch.setattr(cli, "enabled_sources", lambda scheduled_only: [("cs2settings", {})])
    src = _mk_src(
        rosters={"vitality": [{"source_id": "vplayer1", "name": "V1", "role": "igl"}]},
        players={"vplayer1": ParsedPlayer(
            source="cs2settings", source_id="vplayer1", name="V1",
            source_url="fixture://vplayer1", retrieved_at="2026-08-11",
            steam_id="76561198000000002", team=None,  # fallback: no teamId
            role="igl", country="FR", fields={"dpi": 800})},
    )
    monkeypatch.setattr(cli, "get_source", lambda name: src)
    obs, roster, manifest = cli.step_collect(True, False, None, None)
    assert "steam:76561198000000002" in roster["vitality"]
    # player still counted as expected/successful Core player
    assert manifest["expected_core_players"] >= 1
    assert manifest["successful_core_players"] >= 1


# ---------------------------------------------------------------------------
# J. missing manifest fails closed in daily automation
# ---------------------------------------------------------------------------

def test_daily_missing_manifest_fails_closed(monkeypatch, tmp_path):
    calls = []

    def fake_sh(*args, check=True):
        calls.append(list(args))
        return ""

    monkeypatch.setattr(actions_common, "sh", fake_sh)
    monkeypatch.setattr(actions_common, "WORK", tmp_path)
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("PIPELINE_OUTCOME", "success")
    # NO collection-manifest.json written at all
    actions_common.WORK.mkdir(parents=True, exist_ok=True)
    (tmp_path / "drift.json").write_text(json.dumps({"level": 2}))
    (tmp_path / "roster-report.json").write_text(json.dumps({"pending_state": None}))
    (tmp_path / "source-status.json").write_text(json.dumps({"cs2settings": "ok"}))
    (tmp_path / "metrics.json").write_text(json.dumps({"aggregate": {}, "panel": {}}))
    rc = actions_daily.main()
    assert rc == 1  # fail closed: workflow stays red
    # no drift/PR path: no gh pr create call
    assert not [c for c in calls if c[0] == "gh" and c[1] == "pr"]


# ---------------------------------------------------------------------------
# K. weekly uses Core turnover (watchlist churn must not trigger Core warning)
# ---------------------------------------------------------------------------

def test_weekly_core_turnover_guard(monkeypatch, tmp_path):
    calls = []

    def fake_sh(*args, check=True):
        calls.append(list(args))
        return ""

    monkeypatch.setattr(actions_common, "sh", fake_sh)
    monkeypatch.setattr(actions_common, "WORK", tmp_path)
    monkeypatch.setattr(actions_common, "AGG", tmp_path / "agg")
    monkeypatch.setattr(actions_common, "ROOT", REPO)
    # REPORTS/FIGURES MUST be isolated too: the monthly path really calls
    # write_candidate_files, which writes the 4 report files and renders
    # figures — unpatched they would overwrite the REAL repo's public
    # reports/ and figures/latest with test data
    monkeypatch.setattr(actions_common, "REPORTS", tmp_path / "reports")
    monkeypatch.setattr(actions_common, "FIGURES", tmp_path / "figures" / "latest")
    (tmp_path / "agg").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("PIPELINE_OUTCOME", "success")
    (tmp_path / "metrics.json").write_text(json.dumps({
        "aggregate": {"player_count": 100, "scope": {"core_snapshot": "2026-08-10"},
                      "dpi": {"valid_n": 100}, "resolution": {"valid_n": 100},
                      "refresh_rate": {"valid_n": 100}, "fps_max": {"valid_n": 100}},
        "panel": {}}))
    (tmp_path / "drift.json").write_text(json.dumps({"level": 0}))
    (tmp_path / "roster-report.json").write_text(json.dumps({
        "core_turnover_rate": 0.1,   # Core stable
        "turnover_rate": 0.4,        # all-tracked churn (watchlist/HLTV-only)
        "pending_state": None}))
    (tmp_path / "source-status.json").write_text(json.dumps({"cs2settings": "ok"}))
    (tmp_path / "identities.json").write_text(json.dumps({"problems": [], "players": []}))
    (tmp_path / "conflicts.json").write_text(json.dumps([]))
    (tmp_path / "collection-manifest.json").write_text(json.dumps(
        {"collection_complete": True}))
    (tmp_path / "agg" / "latest.json").write_text(json.dumps({
        "aggregate": {"player_count": 100, "dpi": {"valid_n": 100},
                      "resolution": {"valid_n": 100}, "refresh_rate": {"valid_n": 100},
                      "fps_max": {"valid_n": 100}}}))
    rc = actions_weekly.main()
    assert rc == 0
    # no quality issue: Core turnover 10% < 15% despite all-tracked 40%
    assert not [c for c in calls if c[0] == "gh" and c[1] == "issue"]


# ---------------------------------------------------------------------------
# L. activation targets are enforced
# ---------------------------------------------------------------------------

def test_activation_target_enforced(tmp_path):
    from cs2_pro_settings.rankings import RankingError, activate_snapshot

    (tmp_path / "c.yaml").write_text("cohort:\n  core:\n    teams: []\n  reference:\n    teams: []\n")
    vrs = REPO / "config/rankings/valve/2026-08-10.yaml"
    hltv = REPO / "config/rankings/hltv/2026-08-03.yaml"
    # VRS must activate as core, never as reference
    with pytest.raises(RankingError):
        activate_snapshot(vrs, cohort_path=str(tmp_path / "c.yaml"), target="reference")
    # HLTV must activate as reference, never as core
    with pytest.raises(RankingError):
        activate_snapshot(hltv, cohort_path=str(tmp_path / "c.yaml"), target="core")
    activate_snapshot(vrs, cohort_path=str(tmp_path / "c.yaml"), target="core")
    activate_snapshot(hltv, cohort_path=str(tmp_path / "c.yaml"), target="reference")
    import yaml

    out = yaml.safe_load((tmp_path / "c.yaml").read_text())
    assert out["cohort"]["core"]["ranking_authority"] == "valve"
    assert out["cohort"]["reference"]["ranking_authority"] == "hltv"


# ---------------------------------------------------------------------------
# M. VRS importer (provider=valve) shares validation with HLTV importer
# ---------------------------------------------------------------------------

def test_vrs_import_build_snapshot():
    from cs2_pro_settings.rankings import RankingError, build_snapshot

    entries = [(i + 1, f"Team{i}") for i in range(30)]
    snap = build_snapshot(entries, "https://www.hltv.org/valve-ranking/teams/2026/august/10",
                          "2026-08-10", provider="valve", ranking_type="global",
                          mappings=None, allow_unresolved=True)
    assert snap["provider"] == "valve"
    assert snap["ranking_authority"] == "valve"
    assert snap["ranking_type"] == "global"
    assert snap["source_host"] == "www.hltv.org"
    # 29 teams still fails
    with pytest.raises(RankingError):
        build_snapshot(entries[:29], "https://x/", "2026-08-10",
                       provider="valve", ranking_type="global", mappings=None,
                       allow_unresolved=True)
    # duplicate rank fails
    bad = [(1, "A"), (1, "B")] + [(i, f"T{i}") for i in range(3, 31)]
    with pytest.raises(RankingError):
        build_snapshot(bad, "https://x/", "2026-08-10",
                       provider="valve", ranking_type="global", mappings=None,
                       allow_unresolved=True)


def test_cli_import_vrs_subcommand(monkeypatch, tmp_path):
    """import-vrs defaults provider=valve/global and writes to the valve dir."""
    from cs2_pro_settings import cli

    top30 = "\n".join(f"{i+1} Team{i}" for i in range(30)) + "\n"
    f = tmp_path / "t.txt"
    f.write_text(top30)
    out_dir = tmp_path / "snapshots"
    rc = cli.main(["ranking", "import-vrs",
                   "--date", "2026-09-01",
                   "--source-url",
                   "https://www.hltv.org/valve-ranking/teams/2026/september/1",
                   "--file", str(f), "--rankings-dir", str(out_dir),
                   "--no-mapping", "--allow-unresolved"])
    assert rc == 0
    import yaml

    snap = yaml.safe_load((out_dir / "valve" / "2026-09-01.yaml").read_text())
    assert snap["provider"] == "valve"
    assert snap["ranking_type"] == "global"
