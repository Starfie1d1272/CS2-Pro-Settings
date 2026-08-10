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
ISSUE_MAINTENANCE = "[maintenance] HLTV ranking snapshot may need refresh"
MISSINGNESS_PP = 10.0
CONFLICT_RATE = 0.10


def ranking_status() -> dict:
    """Load accepted ranking snapshot + freshness status."""
    cohort = {}
    cp = ROOT / "config" / "cohort.yaml"
    if cp.exists():
        cohort = yaml.safe_load(cp.read_text(encoding="utf-8")) or {}
    core = cohort.get("cohort", {}).get("core", {})
    snapshot_date = core.get("snapshot")
    status = {"snapshot": snapshot_date, "freshness": None, "days": None}
    if snapshot_date:
        from cs2_pro_settings.rankings import freshness
        try:
            name, days = freshness(snapshot_date)
            status["freshness"] = name
            status["days"] = days
        except ValueError:
            status["freshness"] = "unknown"
    return status


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
    baseline_agg = None
    bp = AGG / "latest.json"
    if bp.exists():
        import json
        baseline_agg = json.loads(bp.read_text(encoding="utf-8"))
        if isinstance(baseline_agg, dict) and "aggregate" in baseline_agg:
            baseline_agg = baseline_agg["aggregate"]
    if baseline_agg:
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

    turnover = roster_report.get("turnover_rate")
    if turnover is not None and turnover >= 0.15:
        problems.append(f"roster turnover >= 15%: {turnover}")

    # monthly snapshot publishability: Core initialized + collection
    # complete + core players present (no 0-player / incomplete snapshot)
    manifest = load("collection-manifest.json")
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

    # ranking maintenance: ONLY >=180d triggers an issue (30/90d are status only)
    maintenance_lines: list[str] = []
    if rank.get("freshness") == "maintenance_due":
        maintenance_lines.append(
            f"- HLTV ranking snapshot {rank.get('snapshot')} is "
            f"{rank.get('days')} days old (>=180d); consider importing a new "
            "manual snapshot (ranking import-hltv)")
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
