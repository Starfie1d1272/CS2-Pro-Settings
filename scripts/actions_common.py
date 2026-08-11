#!/usr/bin/env python3
"""Shared GitHub Actions automation helpers.

Pure logic + subprocess; tests mock `sh` (never call GitHub).
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import date
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
AGG = ROOT / "data" / "aggregate"
REPORTS = ROOT / "reports"
FIGURES = ROOT / "figures" / "latest"

PR_BRANCH_PREFIX = "automation/settings-update-"


def sh(*args: str, check: bool = True) -> str:
    """Run a command; module-level so tests can monkeypatch it."""
    r = subprocess.run(args, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"cmd failed: {' '.join(args)}\n{r.stderr}")
    return r.stdout.strip()


def load(name: str) -> dict:
    p = WORK / name
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def dry_run() -> bool:
    return os.environ.get("DRY_RUN", "true").lower() == "true"


def pipeline_outcome() -> str:
    return os.environ.get("PIPELINE_OUTCOME", "success")


def open_issue_number(title_prefix: str) -> Optional[str]:
    out = sh("gh", "issue", "list", "--state", "open", "--limit", "100",
             "--json", "number,title", "--jq",
             f'.[] | select(.title | startswith("{title_prefix}")) | .number')
    return out.splitlines()[0] if out else None


def upsert_issue(title: str, body: str) -> None:
    """Create or update (comment on) a deduplicated issue by title prefix."""
    prefix = title.split(" [")[0]
    num = open_issue_number(prefix)
    if num:
        sh("gh", "issue", "comment", num, "--body", body)
        print(f"updated issue #{num}")
    else:
        sh("gh", "issue", "create", "--title", title, "--body", body)
        print(f"created issue: {title}")


def open_automation_pr() -> Optional[dict]:
    """Existing open candidate PR (branch prefix = canonical dedup key).

    Label-based dedup is NOT required (automated-data-update may not exist).
    """
    out = sh("gh", "pr", "list", "--state", "open", "--limit", "100",
             "--json", "number,headRefName,title", "--jq",
             f'.[] | select(.headRefName | startswith("{PR_BRANCH_PREFIX}")) | '
             r'"\(.number)\t\(.headRefName)"')
    if not out:
        return None
    line = out.splitlines()[0]
    num, head = line.split("\t", 1)
    return {"number": num, "headRefName": head}


def ensure_git_identity() -> None:
    sh("git", "config", "user.name", "github-actions[bot]")
    sh("git", "config", "user.email", "github-actions[bot]@users.noreply.github.com")


def write_candidate_files(metrics: dict, monthly: bool = False) -> list[str]:
    """Update public candidate artifacts; returns changed file descriptions."""
    from cs2_pro_settings.metrics import public_aggregate
    from cs2_pro_settings.plots import render_all

    changed: list[str] = []
    pub = public_aggregate(metrics)
    (AGG / "latest.json").write_text(
        json.dumps(pub, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    changed.append("data/aggregate/latest.json")
    if monthly:
        month_file = AGG / f"{date.today().strftime('%Y-%m')}.json"
        if not month_file.exists():
            month_file.write_text(
                json.dumps(pub, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            changed.append(month_file.name)
    rep = WORK / "report-candidate.md"
    if rep.exists():
        (REPORTS / "latest.md").write_text(rep.read_text(encoding="utf-8"), encoding="utf-8")
        changed.append("reports/latest.md")
    render_all(metrics, FIGURES)
    changed.append("figures/latest/*")
    return changed


def build_pr_body(drift: dict, roster_report: dict, matched_driven: bool = False,
                  monthly: bool = False, changed_files: Optional[list[str]] = None) -> str:
    changed = changed_files or []
    changed_lines = drift.get("changed_metrics", [])
    metrics_lines = "\n".join(
        f"- {c['conclusion']}: {c['baseline']} -> {c['current']} [level {c['level']}]"
        for c in changed_lines) or "- (no conclusion-level change)"
    cc = drift.get("cohort_change", {})
    mp = drift.get("matched_panel_change", {})
    src = load("source-status.json")
    conflicts = load("conflicts.json")
    trigger = "monthly longitudinal snapshot (no headline change required)" if monthly else \
        "matched-panel driven (overall headline suppressed)" if matched_driven else \
        f"drift level {drift.get('level')}"
    return "\n".join([
        "## Trigger",
        f"- {trigger}",
        f"- baseline: {drift.get('baseline_snapshot_date')}",
        f"- candidate: {drift.get('current_snapshot_date')}",
        f"- tracked-team scope status: {'changed' if drift.get('scope_changed') else 'stable'}",
        f"- cohort stability: {drift.get('cohort_stability')} (turnover {drift.get('roster_turnover_rate')})",
        f"- headline suppressed: {drift.get('headline_suppressed')} ({drift.get('suppression_reason', 'n/a')})",
        f"- series compatible: {drift.get('series_compatible')}",
        "",
        "## Cohort",
        f"- old / new player count: {cc.get('baseline_players')} / {cc.get('current_players')}",
        f"- matched player count: {mp.get('matched_count')}",
        "",
        "## Changed conclusions",
        metrics_lines,
        "",
        "## Source status",
        "- " + "; ".join(f"{k}: {v}" for k, v in src.items()),
        f"- conflicts: {len(conflicts) if isinstance(conflicts, list) else conflicts}",
        f"- roster: previous {roster_report.get('previous_total')} / "
        f"current {roster_report.get('current_total')} / matched {roster_report.get('matched_total')}",
        "",
        "## Generated files",
        *(f"- {c}" for c in changed),
        "",
        "## Human review required",
        "This PR contains deterministic data/report updates.",
        "Interpretive conclusions require human review.",
    ])


def create_or_update_candidate_pr(
    drift: dict,
    roster_report: dict,
    metrics: dict,
    matched_driven: bool = False,
    monthly: bool = False,
) -> None:
    """Create or UPDATE the single candidate PR.

    ORDER MATTERS (real git): resolve the target branch FIRST (existing open
    automation PR's real head branch, or a new branch from origin/main), then
    check out that branch, and only THEN write candidate files. Writing
    files before checkout can fail (files written on the wrong branch /
    dirty worktree). No label is required (automated-data-update may not
    exist) and no force push is used.
    """
    ensure_git_identity()
    existing = open_automation_pr()

    if existing:
        head = existing["headRefName"]
        sh("git", "fetch", "origin", head)
        sh("git", "checkout", "-B", head, f"origin/{head}")
    else:
        head = f"{PR_BRANCH_PREFIX}{date.today().strftime('%Y%m%d')}"
        sh("git", "fetch", "origin", "main")
        sh("git", "checkout", "-B", head, "origin/main")

    # NOW write candidate files on the correct branch
    changed_files = write_candidate_files(metrics, monthly=monthly)

    sh("git", "add", "data/aggregate", "reports/latest.md", "figures/latest")
    # commit only if there are changes (no empty commits)
    status = sh("git", "status", "--porcelain")
    if status:
        msg = f"data: update CS2 settings snapshot {date.today().isoformat()}"
        sh("git", "commit", "-m", msg)
    sh("git", "push", "origin", head)  # no --force

    body = build_pr_body(drift, roster_report, matched_driven=matched_driven,
                         monthly=monthly, changed_files=changed_files)
    if existing:
        sh("gh", "pr", "edit", existing["number"], "--body", body)
        print(f"updated PR #{existing['number']} on {head}")
    else:
        title = f"data: update CS2 settings conclusions {date.today().isoformat()}"
        if monthly:
            title = f"data: monthly CS2 settings snapshot {date.today().isoformat()}"
        # explicit --head/--base: the Actions checkout creates the branch
        # without upstream metadata, and gh's upstream inference then
        # aborts ("you must first push the current branch") even though
        # the branch WAS pushed
        sh("gh", "pr", "create", "--title", title, "--body", body,
           "--head", head, "--base", "main")
        print(f"created PR from {head}")
