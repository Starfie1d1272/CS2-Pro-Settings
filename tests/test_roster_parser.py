"""Team roster parser: roster-section membership (role labels optional).

Regression for the HOTU bug: role-less active players were dropped because
the old parser required a role label on the player link. Membership is now
defined by the roster SECTION (semantic heading + container); role is
optional metadata; coach is discovered by the adapter and excluded later by
the pipeline role filter; footer/nav player links never enter the roster.
"""
from pathlib import Path

import pytest

from cs2_pro_settings.cohort import player_allowed
from cs2_pro_settings.sources.base import SourceError
from cs2_pro_settings.sources.cs2settings import CS2SettingsSource

REPO = Path(__file__).resolve().parent.parent
HOTU_FIXTURE = REPO / "tests" / "fixtures" / "cs2settings" / "team-hotu.html"


def _parse(src: CS2SettingsSource, html: str) -> list[dict]:
    orig = src._get_text

    def fake_get(url: str) -> str:
        return html

    src._get_text = fake_get  # type: ignore[method-assign]
    try:
        return src.list_team_roster("hotu")
    finally:
        src._get_text = orig  # type: ignore[method-assign]


@pytest.fixture
def hotu_html() -> str:
    return HOTU_FIXTURE.read_text(encoding="utf-8")


def test_roleless_roster_players_are_parsed(hotu_html):
    """A: role-less roster players are included (membership != role)."""
    roster = _parse(CS2SettingsSource(), hotu_html)
    by_id = {p["source_id"]: p for p in roster}
    assert set(by_id) == {"mizu", "frontales", "dwushka", "n0rb3r7", "kade0", "hotu-coach"}
    assert by_id["mizu"]["role"] == "rifler"
    assert by_id["n0rb3r7"]["role"] == "igl"
    assert by_id["dwushka"]["role"] is None   # role-less
    assert by_id["kade0"]["role"] is None     # role-less
    assert by_id["hotu-coach"]["role"] == "coach"


def test_roleless_player_enters_expected_denominator(hotu_html):
    """B/F: adapter finds 6 (incl. coach); pipeline filter -> 5 active expected."""
    from cs2_pro_settings.cli import load_cohort_config
    from cs2_pro_settings.cohort import excluded_roles

    cfg = load_cohort_config()
    roster = _parse(CS2SettingsSource(), hotu_html)
    active = [p for p in roster if player_allowed(p.get("role"), cfg)[0]]
    assert len(roster) == 6
    assert len(active) == 5                      # coach excluded downstream
    assert {p["source_id"] for p in active} == {
        "mizu", "frontales", "dwushka", "n0rb3r7", "kade0"}


def test_coach_discovered_by_adapter_excluded_by_pipeline(hotu_html):
    """C: adapter returns coach; player_allowed excludes it."""
    from cs2_pro_settings.cli import load_cohort_config

    cfg = load_cohort_config()
    roster = _parse(CS2SettingsSource(), hotu_html)
    coach = next(p for p in roster if p["source_id"] == "hotu-coach")
    allowed, reason = player_allowed(coach["role"], cfg)
    assert allowed is False
    assert "coach" in reason


def test_unrelated_footer_links_never_enter_roster(hotu_html):
    """D: footer 'Popular Players' / 'Browse' links are excluded."""
    roster = _parse(CS2SettingsSource(), hotu_html)
    ids = {p["source_id"] for p in roster}
    assert "m0nesy" not in ids and "niko" not in ids and "karrigan" not in ids
    assert "zywoo" not in ids  # Browse footer link


def test_zero_roster_entries_still_fail_closed():
    """E: reachable page with no roster section -> SourceError."""
    src = CS2SettingsSource()
    html = "<html><body><h1>Team X</h1><p>no roster here</p></body></html>"
    with pytest.raises(SourceError):
        _parse(src, html)
