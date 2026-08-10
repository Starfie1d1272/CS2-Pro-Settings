"""Cohort scope abstraction.

Current v2 scope rule: explicit, versioned tracked-team scope from
config/cohort.yaml (mode: tracked_teams, scope_id: top-tier-plus-selected-v1).

A future RankingBasedScopeProvider is only an interface stub in this round:
no ranking website (HLTV / Valve / Liquipedia / other) has been selected or
audited, and dynamic ranking-based team selection must NOT become a live
dependency before its own source/policy audit. README states this explicitly.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Optional, Protocol

import yaml

from .models import CohortSnapshot

DEFAULT_COHORT_PATH = "config/cohort.yaml"
SCOPE_RULE_VERSION = "tracked-teams-v1"


def scope_hash(scope_id: str, teams: list[str]) -> str:
    payload = json.dumps({"scope_id": scope_id, "teams": sorted(teams)}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class CohortScopeProvider(Protocol):
    """Resolves the tracked-team scope for a pipeline run."""

    def resolve_team_scope(self, observed_at: Optional[str] = None) -> CohortSnapshot: ...


class ConfiguredTeamsScopeProvider:
    """Reads the explicit, versioned team scope from config/cohort.yaml."""

    def __init__(self, config_path: str = DEFAULT_COHORT_PATH) -> None:
        self.config_path = config_path

    def resolve_team_scope(self, observed_at: Optional[str] = None) -> CohortSnapshot:
        with open(self.config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        teams = sorted(cfg.get("teams") or [])
        scope_id = cfg.get("scope_id", "unknown")
        return CohortSnapshot(
            observed_at=observed_at or date.today().isoformat(),
            scope_id=scope_id,
            scope_rule_version=SCOPE_RULE_VERSION,
            teams=teams,
            source="configured",
            scope_hash=scope_hash(scope_id, teams),
        )


class RankingBasedScopeProvider:
    """Interface stub for a FUTURE ranking-backed dynamic team scope.

    Deliberately NOT implemented and NOT networked in this round:
    - no ranking source has been selected;
    - no source/policy audit exists for any ranking website;
    - dynamic scope must not silently change the tracked-team universe.
    """

    def resolve_team_scope(self, observed_at: Optional[str] = None) -> CohortSnapshot:
        raise NotImplementedError(
            "RankingBasedScopeProvider is a planned extension; it requires a "
            "source/policy audit and explicit user opt-in. Current v2 keeps "
            "the team-scope rule explicit and versioned (cohort.yaml)."
        )
