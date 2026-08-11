"""Cohort policy: role filters, tiers, and ranked cohort sets.

Cohort model v4:
- CORE: accepted Valve Global Ranking (VRS) Top 30 snapshot — PRIMARY scope.
- REFERENCE: accepted HLTV World Ranking Top 30 — sensitivity panel.
- CONSENSUS = VRS ∩ HLTV; RANKED UNION = VRS ∪ HLTV.
- WATCHLIST: manual observation choices (never proof of ranking membership).
- SUPPLEMENTAL: legacy/documented teams outside the first-round universe.

Ranking defines competitive scope; the settings source defines observability.
An unresolved settings slug lowers collection coverage only — it never
invalidates a ranking.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Optional

from .rankings import compute_cohort_sets, load_snapshot

TIERS = ("core", "watchlist", "supplemental")

DEFAULT_COHORT_PATH = "config/cohort.yaml"


def excluded_roles(cohort_config: dict) -> set[str]:
    raw = (cohort_config.get("filters") or {}).get("exclude") or []
    return {str(r).strip().lower() for r in raw}


def player_allowed(role: Optional[str], cohort_config: dict) -> tuple[bool, str]:
    """Role-based inclusion. Missing role -> allowed, flagged 'role unknown'.

    Coach / retired / content_creator are excluded per cohort policy; the
    source parser may still SEE them (team pages list coaches), but the
    collect pipeline must drop them from observations, metrics and rosters.
    Role matching normalizes whitespace: 'Content Creator' == 'content_creator'.
    """
    if role is None or not str(role).strip():
        return True, "role unknown"
    r = re.sub(r"\s+", "_", str(role).strip().lower())
    if r in excluded_roles(cohort_config):
        return False, f"excluded role: {r}"
    return True, ""


def _slug_of(item) -> Optional[str]:
    """Core team entries may be slugs or dicts (settings_slug/team_id)."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return item.get("settings_slug") or item.get("team_id")
    return None


def _scope_hash(team_ids: list[str]) -> str:
    return hashlib.sha256(
        json.dumps(sorted(team_ids), sort_keys=True).encode()).hexdigest()[:16]


def load_cohort_sets(cohort_config: Optional[dict] = None) -> dict:
    """Compute ranked cohort sets from the accepted ranking snapshots.

    Returns core/reference/consensus/ranked_union team_id lists (in ranking
    order for core/reference), counts, and hashes. Snapshot files are
    loaded from config/rankings/<provider>/<date>.yaml.
    """
    cfg = cohort_config or {}
    if cfg is None:
        cfg = {}
    core_cfg = cfg.get("cohort", {}).get("core", {})
    ref_cfg = cfg.get("cohort", {}).get("reference", {})
    core_snap = core_cfg.get("snapshot")
    ref_snap = ref_cfg.get("snapshot")
    if not core_snap:
        return {
            "core_teams": [], "reference_teams": [],
            "consensus_teams": [], "ranked_union_teams": [],
            "hltv_only_teams": [], "vrs_only_teams": [],
            "core_count": 0, "reference_count": 0,
            "consensus_count": 0, "ranked_union_count": 0,
            "core_scope_hash": None,
            "unmapped_core_teams": [], "unmapped_reference_teams": [],
        }
    vrs = load_snapshot(core_cfg.get("provider", "valve"), core_snap)
    ref = load_snapshot(ref_cfg.get("provider", "hltv"), ref_snap) if ref_snap else {}
    sets = compute_cohort_sets(vrs, ref if ref else {"teams": []})
    sets["core_scope_hash"] = _scope_hash(sets["core_teams"])
    # team_id -> cs2settings slug map resolved from team-mappings
    # (source_refs), NOT from ranking truth — ranking and source locators
    # are fully separated
    from .rankings import DEFAULT_MAPPINGS, load_mappings, resolve_team_source_ref

    mappings = load_mappings(DEFAULT_MAPPINGS)
    slug_map: dict[str, Optional[str]] = {}
    for snap in (vrs, ref):
        for t in snap.get("teams", []):
            if t.get("team_id") and not t.get("unresolved"):
                slug_map[t["team_id"]] = resolve_team_source_ref(
                    t["team_id"], "cs2settings", mappings)
    sets["slug_map"] = slug_map
    return sets


def team_ids_to_slugs(team_ids: list[str], slug_map: dict) -> list[str]:
    """Map ranked team_ids to settings source slugs (resolved ones only)."""
    return sorted(s for s in (slug_map.get(t) for t in team_ids) if s)


def resolve_team_tier(team_slug: Optional[str], cohort_config: dict) -> Optional[str]:
    """Map a source team slug to its cohort tier (None = not tracked)."""
    if not team_slug:
        return None
    core = cohort_config.get("cohort", {}).get("core", {})
    core_slugs_set = {s for s in (_slug_of(t) for t in (core.get("teams") or [])) if s}
    if team_slug in core_slugs_set:
        return "core"
    watch = cohort_config.get("cohort", {}).get("watchlist") or []
    for item in watch:
        if item.get("settings_slug") == team_slug:
            return "watchlist"
    supp = cohort_config.get("cohort", {}).get("supplemental") or []
    for item in supp:
        if item.get("settings_slug") == team_slug:
            return "supplemental"
    return None


def watchlist_slugs(cohort_config: dict) -> list[str]:
    slugs = []
    for item in cohort_config.get("cohort", {}).get("watchlist") or []:
        if item.get("settings_slug"):
            slugs.append(str(item["settings_slug"]))
    return sorted(slugs)


def tracked_slugs(cohort_config: dict) -> list[str]:
    """Source slugs in the scheduled universe: ranked union ∪ watchlist.

    Ranking teams WITHOUT a settings slug stay in membership truth but do
    not add a source slug (coverage=unresolved, never fabricated).
    HLTV-reference-only teams (union members outside VRS Core) are included
    in the scheduled universe for monitoring. Core team slugs configured
    directly (e.g. test fixtures without ranking snapshots) are honored too.
    """
    slugs: set[str] = set()
    # direct core team slugs (works without ranking snapshots). Uses the
    # SOURCE-specific cs2settings locator (_cs2_slug_of -> source_refs /
    # legacy settings_slug), NEVER the ranking team_id: team_id and source
    # slug are different namespaces (e.g. team_id "natus-vincere" vs
    # cs2settings slug "navi"), and a team_id must never be used as a
    # fetch slug (it 404s and pollutes all_tracked_roster_failures).
    for item in (cohort_config.get("cohort", {}).get("core", {}).get("teams") or []):
        s = _cs2_slug_of(item)
        if s:
            slugs.add(s)
    # ranked union slugs from the accepted snapshots (adds HLTV-only teams)
    sets = load_cohort_sets(cohort_config)
    for tid in sets["ranked_union_teams"]:
        s = (sets.get("slug_map") or {}).get(tid)
        if s:
            slugs.add(s)
    for item in cohort_config.get("cohort", {}).get("watchlist") or []:
        if item.get("settings_slug"):
            slugs.add(str(item["settings_slug"]))
    for item in cohort_config.get("cohort", {}).get("supplemental") or []:
        if item.get("settings_slug"):
            slugs.add(str(item["settings_slug"]))
    return sorted(slugs)


def _cs2_slug_of(item, mappings: Optional[dict] = None) -> Optional[str]:
    """cs2settings locator for a core team entry.

    Entries carry rank/team_id (source-independent). The cs2settings slug
    is resolved from team-mappings source_refs — NEVER stored in ranking
    truth. None = 'no cs2settings page', which does NOT make the team
    unobservable.
    """
    if isinstance(item, str):
        return item  # legacy inline slug
    tid = item.get("team_id") if isinstance(item, dict) else None
    if not tid:
        return None
    if mappings is None:
        from .rankings import DEFAULT_MAPPINGS, load_mappings

        mappings = load_mappings(DEFAULT_MAPPINGS)
    from .rankings import resolve_team_source_ref

    return resolve_team_source_ref(tid, "cs2settings", mappings)


def core_slugs(cohort_config: dict) -> list[str]:
    core = cohort_config.get("cohort", {}).get("core", {})
    mappings = None
    return sorted(s for s in (_cs2_slug_of(t, mappings) for t in (core.get("teams") or [])) if s)
