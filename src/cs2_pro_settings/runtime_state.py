"""Cross-run operational runtime state.

GitHub-hosted runners are ephemeral, so per-run `work/` files cannot carry
roster/matched-panel state between scheduled runs. Production workflows
persist a MINIMAL runtime state via the GitHub Actions cache into
`.runtime-state/` (gitignored):

  roster-previous.json   last successful run's roster (team -> player_ids)
  roster-pending.json    roster change confirmation window
  previous-panel.json    last successful run's Core matched panel
  state-meta.json        warmup/series metadata

Cache semantics:
- the cache is BEST-EFFORT operational state, not a database; a cache miss
  causes a safe warm-up run (state_warmup=true), never a false drift alert;
- previous-panel.json holds ONLY the matched-panel fields (player_id, dpi,
  edpi, resolution, polling_rate, snapshot_date) — never raw HTML, bios, or
  other source content;
- state advances ONLY after a fully successful primary-source pipeline run;
- dry runs never read or write production runtime state.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

STATE_DIR_ENV = "CS2_PRO_RUNTIME_STATE_DIR"
DEFAULT_STATE_DIR = ".runtime-state"

PANEL_FIELDS = ("dpi", "edpi", "resolution", "polling_rate")


def state_dir() -> Path:
    override = os.environ.get(STATE_DIR_ENV)
    return Path(override) if override else Path(DEFAULT_STATE_DIR)


def load_state(name: str) -> Optional[dict]:
    p = state_dir() / name
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def save_state(name: str, obj: dict) -> None:
    p = state_dir() / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def clear_state(name: str) -> None:
    p = state_dir() / name
    p.unlink(missing_ok=True)


def build_previous_panel(metrics: dict) -> dict:
    """Minimal per-player panel for matched-panel drift (Core players only)."""
    panel = metrics.get("panel") or {}
    players = {
        pid: {k: v for k, v in vals.items() if k in PANEL_FIELDS}
        for pid, vals in (panel.get("players") or {}).items()
    }
    return {
        "snapshot_date": (metrics.get("aggregate") or {}).get("snapshot_date"),
        "player_ids": sorted(panel.get("player_ids") or []),
        "players": players,
    }


def compare_panels(previous: dict, current: dict) -> dict:
    """Matched-panel comparison across runs (stable player ids)."""
    prev_ids = set(previous.get("player_ids") or [])
    cur_ids = set(current.get("player_ids") or [])
    matched = sorted(prev_ids & cur_ids)
    prev_players = previous.get("players") or {}
    cur_players = current.get("players") or {}
    per_field: dict[str, dict] = {}
    for fld in PANEL_FIELDS:
        changed = sum(
            1 for pid in matched
            if pid in prev_players and pid in cur_players
            and prev_players[pid].get(fld) != cur_players[pid].get(fld)
        )
        per_field[fld] = {"changed": changed, "compared": len(matched)}
    return {
        "status": "available" if matched else "unavailable",
        "matched_count": len(matched),
        "previous_count": len(prev_ids),
        "current_count": len(cur_ids),
        "per_field": per_field,
    }


def load_previous_panel_for_drift() -> Optional[dict]:
    """Previous panel in the shape compute_drift expects (metrics-like)."""
    prev = load_state("previous-panel.json")
    if prev is None:
        return None
    return {"panel": prev}
