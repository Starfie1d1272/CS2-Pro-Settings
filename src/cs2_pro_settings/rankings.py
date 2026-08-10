"""Manual HLTV ranking snapshots (import / validate / diff / freshness).

HLTV is NEVER scraped. Ranking snapshots are manually entered by maintainers
or contributors, versioned in config/rankings/hltv/YYYY-MM-DD.yaml, and only
activate `cohort.core` after review.

Validation: exactly ranks 1-30, no duplicate rank, no duplicate team,
continuous numbering, source URL and date required, team mapping resolved
(no silent guessing).
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Optional

import yaml

DEFAULT_MAPPINGS = "config/team-mappings.yaml"
DEFAULT_RANKINGS_DIR = "config/rankings/hltv"
DEFAULT_COHORT = "config/cohort.yaml"


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
    mappings: Optional[dict] = None,
    allow_unresolved: bool = False,
) -> dict:
    """Validate + map; returns the snapshot dict (raises RankingError)."""
    validate_entries(entries, source_url, snapshot_date)
    mappings = mappings or load_mappings()
    teams = []
    unresolved: list[str] = []
    for rank, name in entries:
        m = map_team(name, mappings)
        if m is None:
            unresolved.append(name)
            teams.append({"rank": rank, "display_name": name, "unresolved": True})
            continue
        teams.append({
            "rank": rank,
            "display_name": name,
            "team_id": m["team_id"],
            "settings_slug": m.get("settings_slug"),
        })
    if unresolved and not allow_unresolved:
        raise RankingError(
            f"UNRESOLVED teams (no mapping): {', '.join(unresolved)}; "
            "add them to config/team-mappings.yaml")
    return {
        "snapshot_date": snapshot_date,
        "source_url": source_url,
        "imported_at": date.today().isoformat(),
        "top_n": 30,
        "teams": teams,
    }


def save_snapshot(snapshot: dict, rankings_dir: str = DEFAULT_RANKINGS_DIR) -> Path:
    out = Path(rankings_dir) / f"{snapshot['snapshot_date']}.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(snapshot, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return out


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
) -> None:
    """Point cohort.core at an accepted snapshot (must be fully resolved)."""
    snapshot = yaml.safe_load(snapshot_path.read_text(encoding="utf-8")) or {}
    for t in snapshot.get("teams", []):
        if "unresolved" in t or not t.get("settings_slug"):
            raise RankingError(
                f"cannot activate {snapshot_path.name}: contains unresolved "
                "or slug-less teams")
    with open(cohort_path, encoding="utf-8") as f:
        cohort = yaml.safe_load(f) or {}
    cohort.setdefault("cohort", {}).setdefault("core", {})["provider"] = "manual_hltv"
    cohort["cohort"]["core"]["snapshot"] = snapshot["snapshot_date"]
    cohort["cohort"]["core"]["teams"] = [
        {"rank": t["rank"], "team_id": t["team_id"], "settings_slug": t["settings_slug"]}
        for t in snapshot["teams"]
    ]
    with open(cohort_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cohort, f, sort_keys=False, allow_unicode=True)
