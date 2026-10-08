"""Team mapping verification: verified cs2settings team slugs resolve.

The six previously roster-unresolved Core teams (aurora, big, dendele,
hotu, inner-circle, magic) were verified against the live CS2Settings team
pages (HTTP 200, parser OK, roster >= 3) and their source_refs updated.
October adds verified Nemiga, Nemesis, JiJieHao and Luminosity locators.
Historical locator checks remain valid even when a team leaves Core.
"""
import yaml

from cs2_pro_settings.cohort import core_slugs, load_cohort_sets, tracked_slugs
from cs2_pro_settings.rankings import load_mappings, resolve_team_source_ref

MAPPINGS = load_mappings("config/team-mappings.yaml")
COHORT = yaml.safe_load(open("config/cohort.yaml"))


def test_verified_six_team_slugs_resolve():
    for tid, slug in {
        "aurora": "aurora", "big": "big", "dendele": "dendele",
        "hotu": "hotu", "inner-circle": "inner-circle", "magic": "magic",
    }.items():
        assert resolve_team_source_ref(tid, "cs2settings", MAPPINGS) == slug


def test_verified_slugs_enter_core_and_tracked_universe():
    slugs = set(core_slugs(COHORT))
    assert {"aurora", "big", "inner-circle", "magic", "nemiga", "nemesis", "jijiehao", "luminosity"} <= slugs
    assert len(slugs) == 30  # full VRS Core now cs2settings-resolved
    universe = tracked_slugs(COHORT)
    assert "aurora" in universe and "big" in universe


def test_october_ranking_and_aged_reference_sets():
    sets = load_cohort_sets(COHORT)
    assert sets["core_count"] == 30
    assert sets["reference_count"] == 30
    assert sets["consensus_count"] == 24
    assert sets["ranked_union_count"] == 36
