"""Real-git integration: candidate PR branch reuse (no force push).

Creates a temp bare origin + working repo, seeds main and an existing
automation PR branch, then runs create_or_update_candidate_pr with REAL git
commands (gh is mocked). Verifies checkout succeeds, the existing branch is
reused, and the new commit lands on the same branch.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import actions_common  # noqa: E402


def git(cwd: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    assert r.returncode == 0, f"git {args} failed: {r.stderr}"
    return r.stdout.strip()


def _seed_repo(origin: Path, work: Path) -> None:
    git(work, "init", "-q")
    git(work, "config", "user.email", "t@t")
    git(work, "config", "user.name", "t")
    (work / "data" / "aggregate").mkdir(parents=True)
    (work / "reports").mkdir()
    (work / "figures" / "latest").mkdir(parents=True)
    (work / "data" / "aggregate" / "latest.json").write_text(
        json.dumps({"baseline": "2026-05-05"}) + "\n")
    (work / "reports" / "latest.md").write_text("old latest\n")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "main seed")
    git(work, "branch", "-M", "main")
    git(work, "remote", "add", "origin", str(origin))
    git(work, "push", "-q", "origin", "main")
    git(work, "branch", "-q", "automation/settings-update-20260801")
    git(work, "checkout", "-q", "automation/settings-update-20260801")
    (work / "reports" / "latest.md").write_text("old automation content\n")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "existing automation commit")
    git(work, "push", "-q", "origin", "automation/settings-update-20260801")
    git(work, "checkout", "-q", "main")


def test_existing_automation_pr_real_git_branch_reuse(tmp_path, monkeypatch):
    origin = tmp_path / "origin.git"
    work = tmp_path / "work"
    work.mkdir()
    git(work, "init", "-q", "--bare", str(origin))
    _seed_repo(origin, work)

    calls: list = []
    orig_sh = actions_common.sh

    def real_sh(*args, check=True):
        calls.append(list(args))
        if args[0] == "gh":
            if args[1] == "pr" and args[2] == "list":
                return "7\tautomation/settings-update-20260801"
            return ""
        # git: run in working repo
        r = subprocess.run(["git", "-C", str(work), *args[1:]], capture_output=True, text=True)
        if check and r.returncode != 0:
            raise RuntimeError(f"git failed: {r.stderr}")
        return r.stdout.strip()

    monkeypatch.setattr(actions_common, "sh", real_sh)

    metrics = {
        "aggregate": {"snapshot_date": "2026-08-10", "player_count": 5,
                      "team_count": 3, "series": {"series_id": "vrs-core-v2"}},
        "panel": {"status": "available", "player_ids": ["steam:1"]},
    }
    drift = {"level": 2, "baseline_snapshot_date": "2026-08-01",
             "current_snapshot_date": "2026-08-10", "scope_changed": False,
             "cohort_stability": "stable", "roster_turnover_rate": 0.0,
             "headline_suppressed": False, "series_compatible": True,
             "changed_metrics": [], "cohort_change": {},
             "matched_panel_change": {"matched_count": 0}}
    roster = {"previous_total": 5, "current_total": 5, "matched_total": 5}

    # actions_common writes to its own ROOT paths; redirect to the temp repo
    monkeypatch.setattr(actions_common, "ROOT", work)
    monkeypatch.setattr(actions_common, "WORK", work / "work")
    monkeypatch.setattr(actions_common, "AGG", work / "data" / "aggregate")
    monkeypatch.setattr(actions_common, "REPORTS", work / "reports")
    monkeypatch.setattr(actions_common, "FIGURES", work / "figures" / "latest")
    (work / "work").mkdir(exist_ok=True)
    (work / "work" / "report-candidate.md").write_text("candidate\n")

    actions_common.create_or_update_candidate_pr(drift, roster, metrics)

    # assertions on the REAL git state
    assert git(work, "branch", "--show-current") == "automation/settings-update-20260801"
    # existing branch reused: no checkout of a NEW branch, no force push
    assert not any("--force" in c for c in calls)
    assert git(work, "log", "-1", "--oneline") != "existing automation commit"
    # the new commit landed on the SAME branch
    head = git(work, "rev-parse", "HEAD")
    git(work, "fetch", "-q", "origin", "automation/settings-update-20260801")
    assert git(work, "rev-parse", f"origin/automation/settings-update-20260801") == head
    # latest.json updated on the branch
    assert "vrs-core-v2" in (work / "data" / "aggregate" / "latest.json").read_text()
    # main untouched (only the automation branch gained a commit)
    assert git(work, "rev-parse", "origin/main") == git(work, "rev-parse", "main")
