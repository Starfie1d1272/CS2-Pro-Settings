"""Manual HLTV ranking importer: validation, diff, freshness, mapping."""
import pytest

from cs2_pro_settings.rankings import (
    RankingError,
    build_snapshot,
    freshness,
    map_team,
    parse_top30,
    ranking_diff,
    validate_entries,
)

GOOD_TOP30 = "\n".join(f"{i} Team{i}" for i in range(1, 31))
MAPPINGS = {
    "teams": [
        {"display_names": ["Vitality"], "team_id": "vitality", "settings_slug": "vitality"},
        {"display_names": ["Spirit"], "team_id": "team-spirit", "settings_slug": "spirit"},
    ]
}


def test_parse_top30():
    entries = parse_top30("1 Vitality\n2. Spirit\n3) Team\n")
    assert entries == [(1, "Vitality"), (2, "Spirit"), (3, "Team")]


def test_valid_import():
    entries = parse_top30(GOOD_TOP30)
    snap = build_snapshot(entries, "https://hltv.org/ranking", "2026-08-01",
                          mappings={"teams": []}, allow_unresolved=True)
    assert snap["top_n"] == 30
    assert len(snap["teams"]) == 30


@pytest.mark.parametrize("bad", [
    "\n".join(f"{i} Team{i}" for i in range(1, 30)),      # 29 teams
    "\n".join(f"{i} Team{i}" for i in range(1, 32)),      # 31 teams
    "1 TeamA\n1 TeamB\n" + "\n".join(f"{i} Team{i}" for i in range(3, 31)),  # dup rank
    "1 TeamA\n2 TeamA\n" + "\n".join(f"{i} Team{i}" for i in range(3, 31)),  # dup team
    "1 TeamA\n3 TeamB\n" + "\n".join(f"{i} Team{i}" for i in range(4, 32)),  # non-continuous
])
def test_invalid_rankings_fail(bad):
    with pytest.raises(RankingError):
        validate_entries(parse_top30(bad), "https://hltv.org/ranking", "2026-08-01")


def test_missing_url_fails():
    with pytest.raises(RankingError, match="source URL"):
        validate_entries(parse_top30(GOOD_TOP30), "", "2026-08-01")


def test_invalid_date_fails():
    with pytest.raises(RankingError, match="date"):
        validate_entries(parse_top30(GOOD_TOP30), "https://hltv.org/ranking", "not-a-date")


def test_unresolved_mapping_fails():
    text = "1 UnknownTeam\n" + "\n".join(f"{i} Team{i}" for i in range(2, 31))
    with pytest.raises(RankingError, match="UNRESOLVED"):
        build_snapshot(parse_top30(text), "https://hltv.org/ranking", "2026-08-01",
                       mappings=MAPPINGS)


def test_allow_unresolved_marks_candidate():
    text = "1 UnknownTeam\n" + "\n".join(f"{i} Team{i}" for i in range(2, 31))
    snap = build_snapshot(parse_top30(text), "https://hltv.org/ranking", "2026-08-01",
                          mappings=MAPPINGS, allow_unresolved=True)
    assert any("unresolved" in t for t in snap["teams"])


def test_map_team_case_insensitive():
    m = map_team("vitality", MAPPINGS)
    assert m is not None and m["team_id"] == "vitality"
    m2 = map_team("SPIRIT", MAPPINGS)
    assert m2 is not None and m2["team_id"] == "team-spirit"
    assert map_team("nope", MAPPINGS) is None


def test_ranking_diff():
    prev = {"teams": [
        {"rank": 1, "team_id": "a"}, {"rank": 2, "team_id": "b"}, {"rank": 3, "team_id": "c"}]}
    cur = {"teams": [
        {"rank": 1, "team_id": "a"}, {"rank": 2, "team_id": "c"}, {"rank": 3, "team_id": "d"}]}
    diff = ranking_diff(prev, cur)
    assert diff["entered_core"] == ["d"]
    assert diff["exited_core"] == ["b"]
    assert diff["rank_movements"] == [{"team_id": "c", "from": 3, "to": 2}]
    assert any("watchlist review" in s["suggestion"] for s in diff["review_suggestions"])


def test_freshness_bands():
    from datetime import date
    today = date(2026, 8, 10)
    assert freshness("2026-07-25", today)[0] == "fresh"
    assert freshness("2026-06-01", today)[0] == "aging"
    assert freshness("2026-04-01", today)[0] == "stale"
    assert freshness("2025-12-01", today)[0] == "maintenance_due"
