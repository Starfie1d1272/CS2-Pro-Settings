#!/usr/bin/env python3
"""Render accepted-state bilingual snapshot reports from committed aggregates.

The monthly archives and the rolling latest reports are regenerated
deterministically from the ACCEPTED public aggregate — no collection is
performed and no accepted data is overwritten. The minimal run metadata
(source status, conflicts, collection manifest) is reconstructed from the
accepted aggregate plus recorded accepted-run facts, documented below.

Usage (repo root):
    python scripts/render_accepted.py                # latest.json -> latest + YYYY-MM reports
    python scripts/render_accepted.py --month 2026-08
    python scripts/render_accepted.py --no-latest    # archives only
    python scripts/render_accepted.py --latest-only  # latest reports only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from cs2_pro_settings.report import read_legacy_metadata, render_report  # noqa: E402

AGG_DIR = ROOT / "data" / "aggregate"
REPORTS_DIR = ROOT / "reports"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _accepted_metadata(metrics: dict) -> dict:
    """Reconstruct minimal run metadata for the accepted snapshot.

    Source status and conflicts are recorded facts of the accepted run
    (the accepted report listed cs2settings: ok and 0 conflicts). The
    collection manifest is derived from the accepted aggregate:
      - roster coverage = core teams minus source-unresolved teams (an
        unresolved team was never fetched);
      - player fetch = player_count / player_count (the accepted merge gate
        required collection_complete=true, so every roster member with a
        stable identity was fetched; zero-settings players were fetched but
        exposed no settings fields).
    """
    agg = metrics.get("aggregate", {})
    scope = agg.get("scope") or {}
    player_count = agg.get("player_count") or 0
    requested = scope.get("core_team_count") or agg.get("team_count") or 0
    unresolved = len(scope.get("source_unresolved_core_teams") or [])
    roster_ok = max(requested - unresolved, 0)
    manifest = {
        "requested_core_teams": requested,
        "successful_core_team_rosters": roster_ok,
        "expected_core_players": player_count,
        "successful_core_players": player_count,
        "roster_membership_ambiguities": [],
        "collection_complete": True,
    }
    return {
        "source_status": {"cs2settings": "ok"},
        "conflicts": [],
        "manifest": manifest,
    }


def _self_baseline_drift(metrics: dict) -> dict:
    """Drift record for an accepted snapshot whose baseline is itself.

    The accepted baseline (data/aggregate/latest.json) is the SAME snapshot,
    so there is nothing to compare: level 0, no changes, matched panel
    unavailable (public aggregate carries no identity lists).
    """
    agg = metrics.get("aggregate", {})
    player_count = agg.get("player_count") or 0
    date_ = agg.get("snapshot_date")
    return {
        "level": 0,
        "changed_metrics": [],
        "cohort_change": {
            "baseline_players": player_count,
            "current_players": player_count,
            "player_count_delta": 0,
            "added": "unavailable",
            "removed": "unavailable",
        },
        "matched_panel_change": {
            "status": "unavailable",
            "matched_count": 0,
            "note": "no overlap between previous runtime panel and current panel",
        },
        "baseline_snapshot_date": date_,
        "current_snapshot_date": date_,
        "scope_changed": False,
        "cohort_stability": "unavailable",
        "roster_turnover_rate": None,
        "headline_suppressed": False,
        "series_compatible": True,  # same series (self-baseline)
        "baseline_incompatible_reason": "",
    }


def render_accepted(month: str, latest: bool = True, archive: bool = True) -> list[Path]:
    month_path = AGG_DIR / f"{month}.json"
    if not month_path.exists():
        raise SystemExit(f"accepted aggregate not found: {month_path}")
    metrics = _load(month_path)
    baseline = _load(AGG_DIR / "latest.json")
    agg = metrics.get("aggregate", {})
    cur_series = (agg.get("series") or {}).get("series_id")
    legacy = read_legacy_metadata(AGG_DIR, cur_series)
    meta = _accepted_metadata(metrics)
    drift = _self_baseline_drift(metrics)

    written: list[Path] = []
    if latest:
        written.append(_write_pair("latest", metrics, baseline, drift, meta, legacy))
    if archive:
        written.append(_write_pair(month, metrics, baseline, drift, meta, legacy))
    return written


def _write_pair(base: str, metrics: dict, baseline: dict, drift: dict,
                meta: dict, legacy: Optional[dict]) -> Path:
    for locale, suffix in (("en", ".md"), ("zh-CN", ".zh-CN.md")):
        text = render_report(
            metrics=metrics, drift=drift, source_status=meta["source_status"],
            conflicts=meta["conflicts"], baseline=baseline, manifest=meta["manifest"],
            legacy_snapshot=legacy, locale=locale, figure_scope="latest",
            cross_link_base=base,
        )
        out = REPORTS_DIR / f"{base}{suffix}"
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out}")
    return REPORTS_DIR / f"{base}.md"


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", default=None,
                        help="snapshot month (default: month of data/aggregate/latest.json)")
    parser.add_argument("--no-latest", action="store_true", help="skip reports/latest*")
    parser.add_argument("--latest-only", action="store_true", help="only reports/latest*")
    args = parser.parse_args(argv)

    latest_agg = _load(AGG_DIR / "latest.json")
    month = args.month or (latest_agg.get("aggregate", latest_agg).get("snapshot_date") or "")[:7]
    if not month:
        raise SystemExit("cannot determine snapshot month from latest.json")
    render_accepted(month, latest=not args.no_latest, archive=not args.latest_only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
