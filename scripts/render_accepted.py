#!/usr/bin/env python3
"""One-time backfill renderer for the first ACCEPTED vrs-core-v2 baseline.

This script is a ONE-TIME backfill tool for the first accepted `vrs-core-v2`
baseline (2026-08): it renders ONLY that month's archive pair
(reports/2026-08.md + reports/2026-08.zh-CN.md) from the committed accepted
aggregate. The 2026-08 reports are therefore migration/backfill artifacts.

It CANNOT and MUST NOT be used to reconstruct future same-series reports:
drift, roster turnover, matched-panel summaries and source/conflict run
context are not part of the public aggregate, so a byte-for-byte rebuild of
future reports is not possible. Future reports are produced by the pipeline
(`python -m cs2_pro_settings update` -> candidate files -> automation PR)
and accepted via candidate PR review.

Guards:
- Bare invocation (no --month) is REJECTED.
- `reports/2026-05.md` is NEVER writable (legacy preserved).
- ONLY `--month 2026-08` (the first vrs-core-v2 baseline) is allowed; any
  other month is REJECTED to prevent future misuse.
- `reports/latest.*` is NEVER writable by this script: the rolling latest
  pair is produced by the pipeline's candidate flow, and a backfill must
  never overwrite it.

Usage (repo root):
    python scripts/render_accepted.py --month 2026-08
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

LEGACY_MONTH = "2026-05"
# The ONLY month this backfill tool may write: the first accepted
# vrs-core-v2 baseline. Future months are pipeline-generated.
ALLOWED_BACKFILL_MONTHS = ("2026-08",)


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
    This is ONLY valid for the first vrs-core-v2 baseline backfill; future
    same-series reports must use the pipeline's real run context.
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
    unavailable (public aggregate carries no identity lists). Only valid for
    the first-baseline backfill; future reports need the pipeline's drift.
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


def render_accepted(base: str, month_scope: str, metrics: dict) -> Path:
    baseline = _load(AGG_DIR / "latest.json")
    agg = metrics.get("aggregate", {})
    cur_series = (agg.get("series") or {}).get("series_id")
    legacy = read_legacy_metadata(AGG_DIR, cur_series)
    meta = _accepted_metadata(metrics)
    drift = _self_baseline_drift(metrics)
    for locale, suffix in (("en", ".md"), ("zh-CN", ".zh-CN.md")):
        text = render_report(
            metrics=metrics, drift=drift, source_status=meta["source_status"],
            conflicts=meta["conflicts"], baseline=baseline,
            manifest=meta["manifest"], legacy_snapshot=legacy, locale=locale,
            figure_scope=month_scope, cross_link_base=base,
        )
        out = REPORTS_DIR / f"{base}{suffix}"
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out}")
    return REPORTS_DIR / f"{base}.md"


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", default=None,
                        help="backfill a specific accepted month archive "
                             "(only %s)" % " / ".join(ALLOWED_BACKFILL_MONTHS))
    args = parser.parse_args(argv)

    if not args.month:
        raise SystemExit(
            "refusing bare invocation: render_accepted.py is a ONE-TIME "
            "backfill tool for the first vrs-core-v2 baseline; pass "
            f"--month {' / '.join(ALLOWED_BACKFILL_MONTHS)} explicitly")
    if args.month == LEGACY_MONTH:
        raise SystemExit(
            f"refusing to touch the legacy {LEGACY_MONTH} report; "
            "reports/2026-05.md is preserved as-is")
    if args.month not in ALLOWED_BACKFILL_MONTHS:
        raise SystemExit(
            f"refusing --month {args.month}: only "
            f"{' / '.join(ALLOWED_BACKFILL_MONTHS)} may be backfilled by this "
            "script; future same-series reports are generated by the pipeline "
            "(python -m cs2_pro_settings update -> candidate files -> "
            "automation PR)")

    month = args.month
    metrics = _load(AGG_DIR / f"{month}.json")
    render_accepted(month, month_scope=month, metrics=metrics)
    print(f"backfilled archive pair for {month}; reports/latest.* untouched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
