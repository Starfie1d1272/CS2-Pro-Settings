"""Roster drift detection and confirmation state.

A roster change must NOT be notified on first observation: third-party sites
can briefly desync. The confirmation window lives in runtime state
(work/roster-pending.json, gitignored):

- first observed difference  -> status=pending, fingerprint recorded
- next successful run with the SAME fingerprint -> status=confirmed (notify)
- roster back to previous    -> pending cleared
- different fingerprint      -> pending window restarts

turnover_rate = 1 - matched_players / previous_players
(operational stability metric, not statistical significance)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TeamRosterDrift:
    team_id: str
    added_players: list[str] = field(default_factory=list)
    removed_players: list[str] = field(default_factory=list)
    unchanged_players: list[str] = field(default_factory=list)


@dataclass
class RosterReport:
    observed_at: str
    previous_total: int
    current_total: int
    matched_total: int
    team_drifts: list[TeamRosterDrift] = field(default_factory=list)
    has_changes: bool = False

    @property
    def turnover_rate(self) -> Optional[float]:
        if self.previous_total == 0:
            return None
        return round(1 - self.matched_total / self.previous_total, 4)

    def fingerprint(self) -> str:
        """Stable hash of the per-team added/removed diffs."""
        parts = []
        for d in sorted(self.team_drifts, key=lambda t: t.team_id):
            parts.append(json.dumps({
                "team_id": d.team_id,
                "added": d.added_players,
                "removed": d.removed_players,
            }, sort_keys=True))
        payload = "|".join(parts)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def compute_roster_report(
    observed_at: str,
    previous: dict[str, list[str]],
    current: dict[str, list[str]],
) -> RosterReport:
    """Diff per-team rosters (team_id -> sorted stable player_ids)."""
    team_ids = sorted(set(previous) | set(current))
    drifts: list[TeamRosterDrift] = []
    prev_total = 0
    cur_total = 0
    matched_total = 0
    for tid in team_ids:
        p = set(previous.get(tid, []))
        c = set(current.get(tid, []))
        prev_total += len(p)
        cur_total += len(c)
        matched_total += len(p & c)
        added = sorted(c - p)
        removed = sorted(p - c)
        unchanged = sorted(p & c)
        if added or removed:
            drifts.append(TeamRosterDrift(tid, added, removed, unchanged))
    return RosterReport(
        observed_at=observed_at,
        previous_total=prev_total,
        current_total=cur_total,
        matched_total=matched_total,
        team_drifts=drifts,
        has_changes=bool(drifts),
    )


def update_pending_state(pending: Optional[dict], report: RosterReport, observed_at: str) -> Optional[dict]:
    """Transition the confirmation state; returns the new state or None.

    None means "no pending roster change" (state file is removed).
    """
    if not report.has_changes:
        return None
    fp = report.fingerprint()
    if pending and pending.get("fingerprint") == fp:
        return {
            "status": "confirmed",
            "fingerprint": fp,
            "first_observed_at": pending.get("first_observed_at", observed_at),
            "last_observed_at": observed_at,
        }
    return {
        "status": "pending",
        "fingerprint": fp,
        "first_observed_at": observed_at,
        "last_observed_at": observed_at,
    }


def roster_stability(turnover_rate: Optional[float], threshold: float = 0.15) -> str:
    """'stable' | 'unstable' | 'unavailable'."""
    if turnover_rate is None:
        return "unavailable"
    return "unstable" if turnover_rate >= threshold else "stable"
