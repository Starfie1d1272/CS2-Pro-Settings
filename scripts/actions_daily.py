#!/usr/bin/env python3
"""Daily automation decision script (GitHub Actions).

Runs after the pipeline step (which may have failed). Reads work/ artifacts
and PIPELINE_OUTCOME; decides (unless DRY_RUN=true):

- pipeline failure / primary source unhealthy -> [data-source] issue
  (decision step runs `if: always()`; script exits non-zero so the workflow
  stays red), baseline/state NOT updated
- confirmed roster change -> [roster-change] issue (deduplicated)
- drift Level 1 -> [data-drift] issue (deduplicated)
- drift Level 2 (series compatible, scope+roster stable) -> candidate PR
- headline suppressed but matched-panel material change -> matched-panel
  driven candidate PR
- monthly due is handled by the weekly workflow (same candidate PR helper)
"""
from __future__ import annotations

import sys

from actions_common import (
    create_or_update_candidate_pr,
    dry_run,
    load,
    pipeline_outcome,
    upsert_issue,
)

ISSUE_ROSTER = "[roster-change] CS2 tracked rosters changed"
ISSUE_DRIFT = "[data-drift] CS2 pro settings trend update"
ISSUE_SOURCE = "[data-source] CS2 Pro Settings source health"


def main() -> int:
    dr = dry_run()
    print(f"dry_run={dr}")
    outcome = pipeline_outcome()
    print(f"pipeline_outcome={outcome}")

    drift = load("drift.json")
    roster_report = load("roster-report.json")
    source_status = load("source-status.json")
    metrics = load("metrics.json")

    pipeline_failed = outcome != "success"
    primary_ok = str(source_status.get("cs2settings", "missing")).startswith("ok")

    # ---- source health / pipeline failure -------------------------------
    if (pipeline_failed or not primary_ok):
        print("primary source unhealthy or pipeline failed: baseline/state NOT updated")
        if not dr:
            upsert_issue(
                ISSUE_SOURCE,
                "\n".join([
                    "## Status",
                    f"- cs2settings: {source_status.get('cs2settings')}",
                    f"- pipeline outcome: {outcome}",
                    f"- observed: {__import__('datetime').date.today().isoformat()}",
                    "",
                    "Primary source unavailable or pipeline failed: baseline NOT "
                    "updated; runtime state NOT advanced; no data PR created.",
                ]),
            )
            print("source-health issue created/updated")
        else:
            print("(dry-run: no issue)")
        return 1  # workflow stays red

    # ---- roster confirmation ---------------------------------------------
    pending = roster_report.get("pending_state")
    if pending and pending.get("status") == "confirmed":
        print("roster change confirmed")
        if not dr:
            drifts = roster_report.get("team_drifts", [])
            lines = ["## Detected at", f"- {roster_report.get('observed_at')}", "",
                     "## Confirmed changes"]
            for d in drifts:
                lines.append(f"### {d['team_id']}")
                lines.append("OUT:")
                lines += [f"- {p}" for p in d["removed_players"]] or ["- (none)"]
                lines.append("IN:")
                lines += [f"- {p}" for p in d["added_players"]] or ["- (none)"]
            lines += [
                "", "## Cohort impact",
                f"- previous {roster_report.get('previous_total')} / "
                f"current {roster_report.get('current_total')} / "
                f"matched {roster_report.get('matched_total')}",
                f"- turnover {roster_report.get('turnover_rate')}",
                "", "## Sources", "- cs2settings team pages",
                "", "## Settings-analysis status",
                "stable / unstable per config/stability.yaml (15% operational threshold)",
            ]
            upsert_issue(ISSUE_ROSTER, "\n".join(lines))
            print("roster-change issue created/updated")
    else:
        print(f"roster pending state: {pending}")

    # ---- drift ------------------------------------------------------------
    level = drift.get("level", 0)
    series_compatible = drift.get("series_compatible", True)
    suppressed = drift.get("headline_suppressed", False)
    matched = drift.get("matched_panel_change", {})
    per_field = matched.get("per_field") or {}
    material_share = max(
        (v["changed"] / v["compared"] for v in per_field.values() if v.get("compared")),
        default=0.0,
    )

    # matched material threshold from config/stability.yaml
    try:
        import yaml
        stability = yaml.safe_load(open("config/stability.yaml", encoding="utf-8")) or {}
        material_threshold = (stability.get("settings") or {}).get(
            "matched_panel_material_share", 0.50)
    except Exception:
        material_threshold = 0.50
    matched_material = material_share >= material_threshold

    if dr:
        print(f"drift level={level} series_compatible={series_compatible} "
              f"suppressed={suppressed} matched_material={matched_material}")
        return 0

    pr_ok = series_compatible and level >= 2 and not suppressed
    if pr_ok:
        create_or_update_candidate_pr(drift, roster_report, metrics, matched_driven=False)
        print("candidate PR created/updated (Level 2)")
    elif suppressed and matched_material:
        create_or_update_candidate_pr(drift, roster_report, metrics, matched_driven=True)
        print("candidate PR created/updated (matched-panel driven)")
    elif level >= 1:
        changed = drift.get("changed_metrics", [])
        lines = ["## Snapshot",
                 f"- date: {drift.get('current_snapshot_date')}",
                 f"- cohort: {drift.get('cohort_change', {}).get('current_players')} players",
                 f"- stability: {drift.get('cohort_stability')}",
                 f"- series compatible: {series_compatible}",
                 f"- headline suppressed: {suppressed} ({drift.get('suppression_reason', 'n/a')})",
                 "", "## Changed metrics"]
        lines += [f"- {c['conclusion']}: {c['baseline']} -> {c['current']} "
                  f"[level {c['level']}]" for c in changed]
        lines += ["", "## Matched panel",
                  f"- matched {matched.get('matched_count')}",
                  f"- status {matched.get('status')}"]
        upsert_issue(ISSUE_DRIFT, "\n".join(lines))
        print("data-drift issue created/updated")
    else:
        print("level 0: nothing to do")

    return 0


if __name__ == "__main__":
    sys.exit(main())
