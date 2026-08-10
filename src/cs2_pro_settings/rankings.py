"""Manual ranking snapshots (import / validate / diff / freshness).

Rankings are NEVER scraped. Snapshots are manually entered by maintainers or
contributors and versioned under config/rankings/<provider>/<date>.yaml.

Two ranking authorities are supported:
- Valve Global Ranking (VRS) — the project's PRIMARY Core definition
- HLTV World Ranking — REFERENCE / sensitivity panel

Consensus = VRS ∩ HLTV; ranked union = VRS ∪ HLTV. Ranking snapshots define
TEAM MEMBERSHIP IN A RANKING only — player names on ranking pages are never
imported and never treated as current roster truth.

Validation: exactly ranks 1-30, no duplicate rank, no duplicate team,
continuous numbering, source URL and date required. An unresolved SETTINGS
source mapping does NOT invalidate a structurally valid ranking — it only
affects collection coverage.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Optional

import yaml

DEFAULT_MAPPINGS = "config/team-mappings.yaml"
DEFAULT_RANKINGS_ROOT = "config/rankings"
DEFAULT_COHORT = "config/cohort.yaml"

# canonical provider directory names
PROVIDER_DIRS = {"valve": "valve", "hltv": "hltv"}


class RankingError(ValueError):
    pass


def parse_top30(text: str) -> list[tuple[int, str]]:
    """Parse '1 Vitality\\n2 Spirit...' into (rank, display_name) pairs."""
    entries: list[tuple[int, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(\d{1,2})[.\s)]+\s*(.+)$", line)
        if not m:
            raise RankingError(f"unparseable ranking line: {line!r}")
        entries.append((int(m.group(1)), m.group(2).strip()))
    return entries


def validate_entries(
    entries: list[tuple[int, str]],
    source_url: str,
    snapshot_date: str,
) -> None:
    if not source_url or not source_url.startswith(("http://", "https://")):
        raise RankingError("source URL is required (--source-url)")
    try:
        date.fromisoformat(snapshot_date)
    except ValueError as exc:
        raise RankingError(f"invalid snapshot date: {snapshot_date!r}") from exc
    if len(entries) != 30:
        raise RankingError(f"expected exactly 30 teams, got {len(entries)}")
    ranks = [r for r, _ in entries]
    if len(set(ranks)) != 30 or sorted(ranks) != list(range(1, 31)):
        raise RankingError("ranks must be exactly 1..30, unique and continuous")
    names = [n.lower() for _, n in entries]
    if len(set(names)) != 30:
        raise RankingError("duplicate team names in ranking")


def load_mappings(path: str = DEFAULT_MAPPINGS) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def map_team(display_name: str, mappings: dict) -> Optional[dict]:
    """Resolve a display name to a mapping entry (None = unresolved)."""
    target = str(display_name).strip().lower()
    for entry in mappings.get("teams") or []:
        for alias in entry.get("display_names") or []:
            if str(alias).strip().lower() == target:
                return entry
    return None


def build_snapshot(
    entries: list[tuple[int, str]],
    source_url: str,
    snapshot_date: str,
    provider: str = "hltv",
    ranking_type: str = "world",
    mappings: Optional[dict] = None,
    allow_unresolved: bool = False,
) -> dict:
    """Validate + map; returns the snapshot dict (raises RankingError).

    An unresolved SETTINGS source mapping does NOT invalidate the ranking:
    the team stays with `settings_slug: null` and affects collection
    coverage only. `unresolved: true` marks a missing team mapping (no
    canonical team_id), which blocks activation but can still be saved as
    an explicit candidate with --allow-unresolved.
    """
    validate_entries(entries, source_url, snapshot_date)
    mappings = mappings or load_mappings()
    teams = []
    unresolved_ids: list[str] = []
    for rank, name in entries:
        m = map_team(name, mappings)
        if m is None:
            unresolved_ids.append(name)
            teams.append({"rank": rank, "display_name": name, "unresolved": True})
            continue
        teams.append({
            "rank": rank,
            "display_name": name,
            "team_id": m["team_id"],
            "settings_slug": m.get("settings_slug"),
        })
    if unresolved_ids and not allow_unresolved:
        raise RankingError(
            f"UNRESOLVED teams (no mapping): {', '.join(unresolved_ids)}; "
            "add them to config/team-mappings.yaml")
    from urllib.parse import urlparse

    host = urlparse(source_url).netloc or "unknown"
    return {
        "provider": provider,
        "ranking_authority": provider,
        "presentation_host": host,
        "ranking_type": ranking_type,
        "date": snapshot_date,
        "source_url": source_url,
        "source_host": host,
        "imported_at": date.today().isoformat(),
        "top_n": 30,
        "teams": teams,
    }


def snapshot_path(provider: str, snapshot_date: str,
                  root: str = DEFAULT_RANKINGS_ROOT) -> Path:
    d = PROVIDER_DIRS.get(provider, provider)
    return Path(root) / d / f"{snapshot_date}.yaml"


def save_snapshot(snapshot: dict, root: str = DEFAULT_RANKINGS_ROOT) -> Path:
    out = snapshot_path(snapshot.get("provider", "hltv"), snapshot["date"], root=root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(snapshot, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return out


def load_snapshot(provider: str, snapshot_date: str,
                  root: str = DEFAULT_RANKINGS_ROOT) -> dict:
    p = snapshot_path(provider, snapshot_date, root=root)
    if not p.exists():
        raise RankingError(f"snapshot not found: {p}")
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def ranking_team_ids(snapshot: dict) -> list[str]:
    """Canonical team_ids in ranking order (teams without mapping excluded)."""
    ids = []
    for t in snapshot.get("teams", []):
        if t.get("team_id") and not t.get("unresolved"):
            ids.append(t["team_id"])
    return ids


def compute_cohort_sets(vrs: dict, hltv: dict) -> dict:
    """VRS Core + HLTV reference + consensus + ranked union (by team_id).

    Teams without a canonical team_id (unresolved mapping) cannot join the
    consensus/union computation and are reported separately.
    """
    core = ranking_team_ids(vrs)
    ref = ranking_team_ids(hltv)
    core_set, ref_set = set(core), set(ref)
    consensus = sorted(core_set & ref_set)
    union = sorted(core_set | ref_set)
    hltv_only = sorted(ref_set - core_set)
    vrs_only = sorted(core_set - ref_set)
    return {
        "core_teams": core,
        "reference_teams": ref,
        "consensus_teams": consensus,
        "ranked_union_teams": union,
        "hltv_only_teams": hltv_only,
        "vrs_only_teams": vrs_only,
        "core_count": len(core),
        "reference_count": len(ref),
        "consensus_count": len(consensus),
        "ranked_union_count": len(union),
        "unmapped_core_teams": [t["display_name"] for t in vrs.get("teams", [])
                                if t.get("unresolved")],
        "unmapped_reference_teams": [t["display_name"] for t in hltv.get("teams", [])
                                     if t.get("unresolved")],
    }


def ranking_diff(previous: dict, current: dict) -> dict:
    """Compare accepted vs candidate ranking."""
    def keyed(snap: dict) -> dict:
        out = {}
        for t in snap.get("teams", []):
            if "team_id" in t:
                out[t["team_id"]] = t
        return out

    prev = keyed(previous)
    cur = keyed(current)
    entered = sorted(set(cur) - set(prev))
    exited = sorted(set(prev) - set(cur))
    movements = []
    for tid in sorted(set(prev) & set(cur)):
        r_prev = prev[tid].get("rank")
        r_cur = cur[tid].get("rank")
        if r_prev != r_cur:
            movements.append({"team_id": tid, "from": r_prev, "to": r_cur})
    return {
        "entered_core": entered,
        "exited_core": exited,
        "rank_movements": movements,
        "review_suggestions": [
            {"team_id": tid, "suggestion": "exited core -> consider watchlist review"}
            for tid in exited
        ],
    }


def freshness(snapshot_date: str, today: Optional[date] = None) -> tuple[str, int]:
    """Return (status, days_since): fresh / aging / stale / maintenance_due."""
    d = date.fromisoformat(snapshot_date)
    days = (today or date.today()) - d
    n = days.days
    if n < 30:
        return "fresh", n
    if n < 90:
        return "aging", n
    if n < 180:
        return "stale", n
    return "maintenance_due", n


def activate_snapshot(
    snapshot_path: Path,
    cohort_path: str = DEFAULT_COHORT,
    provider: Optional[str] = None,
) -> None:
    """Point cohort.core at an accepted ranking snapshot.

    Structural validity only: ranks must be complete and every team must
    have a canonical team_id (no `unresolved`). Teams WITHOUT a settings
    source slug are valid — they affect collection coverage, not ranking
    truth (ranking defines competitive scope; the settings source defines
    observability; never conflate them).
    """
    snapshot = yaml.safe_load(snapshot_path.read_text(encoding="utf-8")) or {}
    for t in snapshot.get("teams", []):
        if t.get("unresolved"):
            raise RankingError(
                f"cannot activate {snapshot_path.name}: contains unresolved "
                "team mapping (no canonical team_id)")
    provider = provider or snapshot.get("provider", "hltv")
    with open(cohort_path, encoding="utf-8") as f:
        cohort = yaml.safe_load(f) or {}
    core = cohort.setdefault("cohort", {}).setdefault("core", {})
    core["provider"] = provider
    core["ranking_authority"] = snapshot.get("ranking_authority", provider)
    core["ranking_type"] = snapshot.get("ranking_type", "global")
    core["snapshot"] = snapshot["date"]
    core["teams"] = [
        {"rank": t["rank"], "team_id": t["team_id"], "settings_slug": t.get("settings_slug")}
        for t in snapshot["teams"]
    ]
    with open(cohort_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cohort, f, sort_keys=False, allow_unicode=True)
