#!/usr/bin/env python3
"""Daily automation decision script (GitHub Actions).

Reads work/ artifacts produced by `python -m cs2_pro_settings update --scheduled`
and decides (unless DRY_RUN=true):

- confirmed roster change  -> [roster-change] issue (deduplicated)
- drift Level 1            -> [data-drift] issue (deduplicated)
- drift Level 2            -> candidate PR (deduplicated on automation branch)
- headline suppressed but matched-panel material change -> matched-panel
  driven candidate PR (same deduplication)
- primary source unhealthy -> [data-source] issue (deduplicated)

Dry-run: live pipeline already ran; NO issues, commits, or PRs are created.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"

ISSUE_ROSTER = "[roster-change] CS2 tracked rosters changed"
ISSUE_DRIFT = "[data-drift] CS2 pro settings trend update"
ISSUE_SOURCE = "[data-source] CS2 Pro Settings source health"
LABEL_AUTO = "automated-data-update"
PR_BRANCH_PREFIX = "automation/settings-update-"


def load(name: str) -> dict:
    p = WORK / name
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def sh(*args: str, check: bool = True) -> str:
    r = subprocess.run(args, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"cmd failed: {' '.join(args)}\n{r.stderr}")
    return r.stdout.strip()


def open_issue_number(title_prefix: str) -> str | None:
    out = sh("gh", "issue", "list", "--state", "open", "--limit", "100",
             "--json", "number,title", "--jq",
             f'.[] | select(.title | startswith("{title_prefix}")) | .number')
    return out.splitlines()[0] if out else None


def upsert_issue(title: str, body: str) -> None:
    num = open_issue_number(title.split(" [")[0])
    if num:
        sh("gh", "issue", "comment", num, "--body", body)
        print(f"updated issue #{num}")
    else:
        sh("gh", "issue", "create", "--title", title, "--body", body)
        print(f"created issue: {title}")


def open_automation_pr() -> str | None:
    out = sh("gh", "pr", "list", "--state", "open", "--limit", "100",
             "--json", "headRefName,number,title", "--jq",
             ".[] | select(.headRefName | startswith(\"automation/settings-update-\")) | .number")
    return out.splitlines()[0] if out else None


def candidate_pr(drift: dict, roster_report: dict, metrics: dict, matched_driven: bool = False) -> None:
    today = date.today()
    branch = f"{PR_BRANCH_PREFIX}{today.strftime('%Y%m%d')}"
    existing = open_automation_pr()
    sh("git", "config", "user.name", "github-actions[bot]")
    sh("git", "config", "user.email", "github-actions[bot]@users.noreply.github.com")

    # update public artifacts
    from cs2_pro_settings.metrics import public_aggregate
    from cs2_pro_settings.plots import render_all

    pub = public_aggregate(metrics)
    agg_dir = ROOT / "data" / "aggregate"
    (agg_dir / "latest.json").write_text(json.dumps(pub, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # monthly snapshot if none for this month yet
    month_file = agg_dir / f"{today.strftime('%Y-%m')}.json"
    if not month_file.exists():
        month_file.write_text(json.dumps(pub, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (ROOT / "reports" / "latest.md").write_text(
        (WORK / "report-candidate.md").read_text(encoding="utf-8"), encoding="utf-8")
    figures = ROOT / "figures" / "latest"
    render_all(metrics, figures)

    changed = drift.get("changed_metrics", [])
    changed_lines = "\n".join(
        f"- {c['conclusion']}: {c['baseline']} -> {c['current']} [level {c['level']}]" for c in changed)
    if not changed_lines:
        changed_lines = "- (no conclusion-level change; matched-panel driven)"
    cc = drift.get("cohort_change", {})
    mp = drift.get("matched_panel_change", {})
    src = load("source-status.json")
    conflicts = load("conflicts.json")
    rr = roster_report
    body = "\n".join([
        "## Trigger",
        f"- baseline: {drift.get('baseline_snapshot_date')}",
        f"- candidate: {drift.get('current_snapshot_date')}",
        f"- tracked-team scope status: {'changed' if drift.get('scope_changed') else 'stable'}",
        f"- cohort stability: {drift.get('cohort_stability')} (turnover {drift.get('roster_turnover_rate')})",
        f"- headline suppressed: {drift.get('headline_suppressed')} ({drift.get('suppression_reason', 'n/a')})",
        f"- matched-panel driven: {matched_driven}",
        "",
        "## Cohort",
        f"- old / new player count: {cc.get('baseline_players')} / {cc.get('current_players')}",
        f"- matched player count: {mp.get('matched_count')}",
        "",
        "## Changed conclusions",
        changed_lines,
        "",
        "## Source status",
        "- " + "; ".join(f"{k}: {v}" for k, v in src.items()),
        f"- conflicts: {len(conflicts) if isinstance(conflicts, list) else conflicts}",
        f"- roster: previous {rr.get('previous_total')} / current {rr.get('current_total')} / matched {rr.get('matched_total')}",
        "",
        "## Generated files",
        "- data/aggregate/latest.json",
        "- data/aggregate/YYYY-MM.json (if month was missing)",
        "- reports/latest.md",
        "- figures/latest/*",
        "",
        "## Human review required",
        "This PR contains deterministic data/report updates.",
        "Interpretive conclusions require human review.",
    ])
    if existing:
        sh("git", "checkout", "-B", branch, "origin/main")
    else:
        sh("git", "checkout", "-b", branch)
    sh("git", "add", "data/aggregate", "reports/latest.md", "figures/latest")
    sh("git", "commit", "-m", f"data: update CS2 settings snapshot {today.isoformat()}", check=False)
    sh("git", "push", "origin", branch, "--force")
    if existing:
        sh("gh", "pr", "edit", existing, "--body", body)
        print(f"updated PR #{existing} on {branch}")
    else:
        sh("gh", "pr", "create", "--title",
           f"data: update CS2 settings conclusions {today.isoformat()}",
           "--body", body, "--label", LABEL_AUTO)
        print(f"created PR from {branch}")


def main() -> int:
    dry_run = os.environ.get("DRY_RUN", "true").lower() == "true"
    print(f"dry_run={dry_run}")

    drift = load("drift.json")
    roster_report = load("roster-report.json")
    source_status = load("source-status.json")
    metrics = load("metrics.json")

    # ---- source health (primary) ---------------------------------------
    primary_ok = str(source_status.get("cs2settings", "missing")).startswith("ok")
    if not primary_ok and not dry_run:
        upsert_issue(ISSUE_SOURCE,
                     f"## Status\n- cs2settings: {source_status.get('cs2settings')}\n"
                     f"- observed: {date.today().isoformat()}\n\nPrimary source unavailable: "
                     "baseline NOT updated; workflow considered failed.")
        print("source health issue created/updated")
    elif not primary_ok:
        print("primary source unhealthy (dry-run: no issue)")

    # ---- roster confirmation -------------------------------------------
    pending = roster_report.get("pending_state")
    if pending and pending.get("status") == "confirmed" and not dry_run:
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
            f"- previous {roster_report.get('previous_total')} / current {roster_report.get('current_total')} / matched {roster_report.get('matched_total')}",
            f"- turnover {roster_report.get('turnover_rate')}",
            "", "## Sources", "- cs2settings team pages",
            "", "## Settings-analysis status",
            "stable / unstable per config/stability.yaml (15% operational threshold)",
        ]
        upsert_issue(ISSUE_ROSTER, "\n".join(lines))
        print("roster-change issue created/updated")
    elif pending and pending.get("status") == "confirmed":
        print("roster change confirmed (dry-run: no issue)")

    # ---- drift -----------------------------------------------------------
    level = drift.get("level", 0)
    matched = drift.get("matched_panel_change", {})
    per_field = matched.get("per_field") or {}
    material_share = max((v["changed"] / v["compared"] for v in per_field.values() if v.get("compared")), default=0.0)
    matched_material = material_share >= 0.5
    suppressed = drift.get("headline_suppressed", False)

    if dry_run:
        print(f"drift level={level} suppressed={suppressed} matched_material={matched_material}")
        return 0

    if level >= 2 and not suppressed:
        candidate_pr(drift, roster_report, metrics, matched_driven=False)
        print("candidate PR created/updated (Level 2)")
    elif suppressed and matched_material:
        candidate_pr(drift, roster_report, metrics, matched_driven=True)
        print("candidate PR created/updated (matched-panel driven)")
    elif level >= 1:
        changed = drift.get("changed_metrics", [])
        lines = ["## Snapshot",
                 f"- date: {drift.get('current_snapshot_date')}",
                 f"- cohort: {drift.get('cohort_change', {}).get('current_players')} players",
                 f"- stability: {drift.get('cohort_stability')}",
                 f"- headline suppressed: {suppressed} ({drift.get('suppression_reason', 'n/a')})",
                 "", "## Changed metrics"]
        lines += [f"- {c['conclusion']}: {c['baseline']} -> {c['current']} [level {c['level']}]" for c in changed]
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
