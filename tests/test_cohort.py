"""Cohort policy: role filters and tier resolution."""
from cs2_pro_settings.cohort import (
    core_slugs,
    player_allowed,
    resolve_team_tier,
    tracked_slugs,
)

CONFIG = {
    "filters": {"exclude": ["coach", "retired", "content_creator"]},
    "cohort": {
        "core": {"teams": [{"rank": 1, "team_id": "vitality", "settings_slug": "vitality"}]},
        "watchlist": [{"team_id": "100-thieves", "settings_slug": "100-thieves"}],
        "supplemental": [{"team_id": "mouz", "settings_slug": "mouz"}],
    },
}


def test_coach_excluded():
    allowed, reason = player_allowed("Coach", CONFIG)
    assert allowed is False
    assert "coach" in reason


def test_retired_and_content_creator_excluded():
    assert player_allowed("Retired", CONFIG)[0] is False
    assert player_allowed("Content Creator", CONFIG)[0] is False


def test_case_insensitive():
    assert player_allowed("COACH", CONFIG)[0] is False


def test_active_roles_allowed():
    assert player_allowed("Rifler", CONFIG)[0] is True
    assert player_allowed("AWPer", CONFIG)[0] is True
    assert player_allowed("IGL", CONFIG)[0] is True


def test_missing_role_allowed_flagged_unknown():
    allowed, reason = player_allowed(None, CONFIG)
    assert allowed is True
    assert reason == "role unknown"


def test_tier_resolution():
    assert resolve_team_tier("vitality", CONFIG) == "core"
    assert resolve_team_tier("100-thieves", CONFIG) == "watchlist"
    assert resolve_team_tier("mouz", CONFIG) == "supplemental"
    assert resolve_team_tier("unknown", CONFIG) is None
    assert resolve_team_tier(None, CONFIG) is None


def test_tracked_universe_and_core():
    assert tracked_slugs(CONFIG) == ["100-thieves", "mouz", "vitality"]
    assert core_slugs(CONFIG) == ["vitality"]
