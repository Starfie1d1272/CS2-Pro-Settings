#!/usr/bin/env python3
"""Weekly reconciliation decision script (GitHub Actions).

- source health / identity / missingness / conflict audits
- ranking freshness (>=180d -> deduplicated [maintenance] issue; 30/90d are
  status-only, never spamming)
- watchlist review_due surfacing (same [maintenance] issue)
- monthly snapshot: when data/aggregate/YYYY-MM.json is missing, REALLY
  create/update the candidate automation PR (Level 0 allowed; merged into an
  existing automation PR if one is open)
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Optional

import yaml

from actions_common import (
    AGG,
    ROOT,
    create_or_update_candidate_pr,
    dry_run,
    load,
    open_issue_number,
    pipeline_outcome,
    upsert_issue,
)

ISSUE_QUALITY = "[data-quality] CS2 Pro Settings pipeline health"
ISSUE_MAINTENANCE = "[maintenance] CS2 ranking snapshots may need refresh"
MISSINGNESS_PP = 10.0
CONFLICT_RATE = 0.10


def _snapshot_freshness(snapshot_date: Optional[str]) -> dict:
    if not snapshot_date:
        return {"snapshot": None, "freshness": None, "days": None}
    from cs2_pro_settings.rankings import freshness

    try:
        name, days = freshness(snapshot_date)
        return {"snapshot": snapshot_date, "freshness": name, "days": days}
    except ValueError:
        return {"snapshot": snapshot_date, "freshness": "unknown", "days": None}


def ranking_status() -> dict:
    """Freshness of the accepted ranking snapshots — Core and reference SEPARATE.

    A stale VRS snapshot is reported as VRS stale; a stale HLTV snapshot as
    HLTV stale. They are never conflated.
    """
    cohort = {}
    cp = ROOT / "config" / "cohort.yaml"
    if cp.exists():
        cohort = yaml.safe_load(cp.read_text(encoding="utf-8")) or {}
    c = cohort.get("cohort", {})
    core = c.get("core", {})
    ref = c.get("reference", {})
    return {
        "core": {
            "provider": core.get("provider", "valve"),
            **_snapshot_freshness(core.get("snapshot")),
        },
        "reference": {
            "provider": ref.get("provider", "hltv"),
            **_snapshot_freshness(ref.get("snapshot")),
        },
    }


def watchlist_review_due(today: Optional[date] = None) -> list[str]:
    """Watchlist items whose review timer expired.

    reference_date = last_reviewed OR added_at (never 'missing' alone).
    review_due only when today - reference_date >= maintenance window
    (default 180 days). Items added yesterday must NOT be due.
    """
    from datetime import timedelta  # noqa: F401

    today = today or date.today()
    cohort_path = ROOT / "config" / "cohort.yaml"
    if not cohort_path.exists():
        return []
    cohort = yaml.safe_load(cohort_path.read_text(encoding="utf-8")) or {}
    items = cohort.get("cohort", {}).get("watchlist") or []
    freshness = cohort.get("ranking_freshness") or {}
    window = int(freshness.get("maintenance_days", 180))
    due = []
    for item in items:
        status = (item.get("status") or "").lower()
        if status == "retired":
            continue
        ref = item.get("last_reviewed") or item.get("added_at")
        if not ref:
            continue  # no reference date -> not due (conservative)
        try:
            ref_date = date.fromisoformat(str(ref)[:10])
        except ValueError:
            continue
        if (today - ref_date).days >= window:
            due.append(item.get("team_id", "?"))
    return due


def main() -> int:
    dr = dry_run()
    print(f"dry_run={dr}")
    outcome = pipeline_outcome()
    print(f"pipeline_outcome={outcome}")

    drift = load("drift.json")
    roster_report = load("roster-report.json")
    source_status = load("source-status.json")
    metrics = load("metrics.json")
    identities = load("identities.json")
    conflicts = load("conflicts.json")

    problems: list[str] = []

    if outcome != "success":
        problems.append(f"pipeline outcome: {outcome}")

    primary = source_status.get("cs2settings", "missing")
    if not str(primary).startswith("ok"):
        problems.append(f"primary source unavailable: cs2settings={primary}")

    id_problems = identities.get("problems") or []
    if id_problems:
        problems.append(
            f"identity problems: {len(id_problems)} "
            f"({', '.join(p.get('type', '?') for p in id_problems[:5])})")

    n_conflicts = len(conflicts) if isinstance(conflicts, list) else 0
    n_players = metrics.get("aggregate", {}).get("player_count", 0)
    if n_players and n_conflicts / max(n_players, 1) >= CONFLICT_RATE:
        problems.append(f"conflict rate >= 10%: {n_conflicts}/{n_players}")

    agg = metrics.get("aggregate", {})
    # missingness spike vs baseline ONLY when the series are comparable AND
    # the current collection is complete (legacy 2026-05 vs vrs-core-v2 must
    # never produce a longitudinal missingness warning)
    manifest = load("collection-manifest.json")
    cur_series = (agg.get("series") or {}).get("series_id")
    manifest_ok = bool(manifest.get("collection_complete", False)) if manifest else False
    baseline_agg = None
    bp = AGG / "latest.json"
    if bp.exists():
        import json
        baseline_agg = json.loads(bp.read_text(encoding="utf-8"))
        if isinstance(baseline_agg, dict) and "aggregate" in baseline_agg:
            baseline_agg = baseline_agg["aggregate"]
    base_series = (baseline_agg or {}).get("series", {}).get("series_id")
    series_compatible = bool(cur_series and cur_series == base_series)
    if baseline_agg and series_compatible and manifest_ok:
        for field in ("dpi", "resolution", "refresh_rate", "fps_max"):
            cur = agg.get(field, {})
            base = baseline_agg.get(field, {})
            cur_n = cur.get("valid_n")
            base_n = base.get("valid_n")
            cur_players = agg.get("player_count", 0)
            base_players = baseline_agg.get("player_count", 0)
            if cur_n is not None and base_n is not None and cur_players and base_players:
                cur_miss = 1 - cur_n / cur_players
                base_miss = 1 - base_n / base_players
                if (cur_miss - base_miss) * 100 >= MISSINGNESS_PP:
                    problems.append(
                        f"missingness spike >= 10pp in {field}: "
                        f"{base_miss*100:.1f}% -> {cur_miss*100:.1f}%")
    elif baseline_agg and not series_compatible:
        print(f"series incompatible ({base_series} -> {cur_series}): "
              "no longitudinal missingness comparison; current absolute "
              f"field coverage reported only ({agg.get('player_count', 0)} players)")

    # Core-only turnover drives the headline quality guard; all-tracked
    # turnover is reported separately for monitoring (Watchlist / HLTV-only
    # roster churn must NOT trigger the Core >=15% quality warning)
    turnover = roster_report.get("core_turnover_rate", roster_report.get("turnover_rate"))
    all_tracked_turnover = roster_report.get("turnover_rate")
    if turnover is not None and turnover >= 0.15:
        problems.append(f"Core roster turnover >= 15%: {turnover}")
    print(f"all_tracked_turnover: {all_tracked_turnover}")

    # monthly snapshot publishability: Core initialized + collection
    # complete + core players present (no 0-player / incomplete snapshot)
    collection_complete = bool(manifest.get("collection_complete", False)) if manifest else False
    core_player_count = metrics.get("aggregate", {}).get("player_count", 0)
    core_initialized = bool((metrics.get("aggregate", {}).get("scope") or {}).get("core_snapshot"))
    collection_publishable = (core_initialized and collection_complete and core_player_count > 0)

    month_file = AGG / f"{date.today().strftime('%Y-%m')}.json"
    monthly_due = not month_file.exists()

    rank = ranking_status()
    watch_due = watchlist_review_due()
    print(f"ranking: {rank}")
    print(f"watchlist review due: {watch_due}")
    print(f"monthly snapshot due: {monthly_due}")
    print(f"collection_publishable: {collection_publishable}")
    print("problems:", problems or "none")

    if dr:
        return 0

    if problems:
        body = "\n".join([
            "## Pipeline health",
            f"- checked: {date.today().isoformat()}",
            "", "## Problems",
        ] + [f"- {p}" for p in problems] + [
            "", "## Context",
            f"- drift level: {drift.get('level')}",
            f"- roster turnover: {turnover}",
            f"- scope: {agg.get('scope', {}).get('scope_id')}",
        ])
        upsert_issue(ISSUE_QUALITY, body)
        print("data-quality issue created/updated")

    # ranking maintenance: ONLY >=180d triggers an issue (30/90d are status
    # only); Core (VRS) and reference (HLTV) freshness are evaluated
    # SEPARATELY and never conflated
    maintenance_lines: list[str] = []
    for key, label, importer in (("core", "Valve Global Ranking (VRS)", "import-vrs"),
                                 ("reference", "HLTV World Ranking", "import-hltv")):
        rs = rank.get(key, {})
        if rs.get("freshness") == "maintenance_due":
            maintenance_lines.append(
                f"- {label} snapshot {rs.get('snapshot')} is "
                f"{rs.get('days')} days old (>=180d); consider importing a "
                f"new manual snapshot (ranking {importer})")
    if watch_due:
        maintenance_lines.append(
            "- watchlist items without last_reviewed (review_due): "
            + ", ".join(watch_due))
    if maintenance_lines:
        body = "\n".join([
            "## Maintenance",
            f"- checked: {date.today().isoformat()}",
            "",
        ] + maintenance_lines + [
            "",
            "Not auto-modified: ranking/watchlist changes require human review.",
        ])
        upsert_issue(ISSUE_MAINTENANCE, body)
        print("maintenance issue created/updated")

    # monthly snapshot: REALLY create/update the candidate PR (Level 0 ok)
    # but ONLY when the collection is publishable (Core initialized,
    # complete, players present) — never a 0-player / incomplete snapshot
    if monthly_due:
        if collection_publishable:
            print("monthly snapshot due + publishable -> candidate PR")
            create_or_update_candidate_pr(drift, roster_report, metrics, monthly=True)
            print("monthly snapshot candidate PR created/updated")
        else:
            print("monthly snapshot due but NOT publishable "
                  f"(core_initialized={core_initialized}, "
                  f"collection_complete={collection_complete}, "
                  f"core_player_count={core_player_count}); no candidate")
            if not problems:
                upsert_issue(
                    ISSUE_QUALITY,
                    "\n".join([
                        "## Monthly snapshot blocked",
                        f"- checked: {date.today().isoformat()}",
                        f"- collection_publishable: false "
                        f"(core_initialized={core_initialized}, "
                        f"collection_complete={collection_complete}, "
                        f"core_player_count={core_player_count})",
                        "No monthly snapshot candidate was created.",
                    ]),
                )
                print("monthly-blocked quality issue created/updated")

    return 0


if __name__ == "__main__":
    sys.exit(main())
