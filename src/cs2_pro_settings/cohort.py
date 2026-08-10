"""Cohort policy: role filters and Core/Watchlist/Supplemental tiers.

Cohort model v3:
- CORE: strictly defined by the last accepted manual HLTV Top 30 snapshot
  (config/rankings/hltv/YYYY-MM-DD.yaml). Core only feeds headline metrics.
- WATCHLIST: near-top30 / rising teams worth observing (manual, not proof of
  HLTV rank).
- SUPPLEMENTAL: regional / notable / legacy-selected teams.

Tracked universe = Core ∪ Watchlist ∪ Supplemental. Core headline statistics
must never be polluted by extended-cohort drift.
"""
from __future__ import annotations

import re
from typing import Optional

TIERS = ("core", "watchlist", "supplemental")


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


def tracked_slugs(cohort_config: dict) -> list[str]:
    """All source slugs in the tracked universe (deduplicated, sorted)."""
    slugs: set[str] = set()
    core = cohort_config.get("cohort", {}).get("core", {})
    slugs.update(s for s in (_slug_of(t) for t in (core.get("teams") or [])) if s)
    for item in cohort_config.get("cohort", {}).get("watchlist") or []:
        if item.get("settings_slug"):
            slugs.add(str(item["settings_slug"]))
    for item in cohort_config.get("cohort", {}).get("supplemental") or []:
        if item.get("settings_slug"):
            slugs.add(str(item["settings_slug"]))
    return sorted(slugs)


def core_slugs(cohort_config: dict) -> list[str]:
    core = cohort_config.get("cohort", {}).get("core", {})
    return sorted(s for s in (_slug_of(t) for t in (core.get("teams") or [])) if s)
