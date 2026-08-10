"""Automation decision tests: mocked subprocess (no GitHub calls)."""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import actions_common  # noqa: E402
import actions_daily  # noqa: E402


@pytest.fixture(autouse=True)
def _patch_sh(monkeypatch):
    """Replace subprocess calls with an in-memory fake gh/git."""
    calls: list[list[str]] = []
    state = {"issues": [], "prs": []}

    def fake_sh(*args, check=True):
        calls.append(list(args))
        cmd = args[0]
        if cmd == "gh" and args[1] == "issue":
            if args[2] == "list":
                return "\n".join(i["number"] for i in state["issues"] if i["open"])
            if args[2] == "create":
                state["issues"].append({"number": str(len(state["issues"]) + 1), "open": True})
                return ""
            if args[2] == "comment":
                return ""
        if cmd == "gh" and args[1] == "pr":
            if args[2] == "list":
                return "\n".join(
                    f"{p['number']}\t{p['head']}" for p in state["prs"] if p["open"])
            if args[2] == "create":
                state["prs"].append({"number": str(len(state["prs"]) + 1), "open": True,
                                     "head": f"automation/settings-update-{args[-2] if len(args) > 2 else 'x'}"})
                return ""
            if args[2] == "edit":
                return ""
        if cmd == "git":
            return ""
        return ""

    monkeypatch.setattr(actions_common, "sh", fake_sh)
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("PIPELINE_OUTCOME", "success")
    yield state, calls


def _write_work(name: str, obj):
    p = Path("work") / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj), encoding="utf-8")


def _base_drift(level=0, suppressed=False, series_ok=True):
    return {
        "level": level,
        "changed_metrics": [] if level == 0 else [{"conclusion": "x", "baseline": "1",
                                                   "current": "2", "level": 1}],
        "cohort_change": {"baseline_players": 100, "current_players": 100},
        "matched_panel_change": {"status": "available", "matched_count": 90,
                                 "per_field": {"dpi": {"changed": 5, "compared": 90}}},
        "baseline_snapshot_date": "2026-05-05",
        "current_snapshot_date": "2026-08-01",
        "scope_changed": False,
        "scope_warning": "",
        "cohort_stability": "stable",
        "roster_turnover_rate": 0.05,
        "headline_suppressed": suppressed,
        "suppression_reason": "" if not suppressed else "high roster turnover",
        "series_compatible": series_ok,
        "baseline_incompatible_reason": "" if series_ok else "incompatible",
    }


def test_dry_run_zero_writes(monkeypatch, _patch_sh):
    state, calls = _patch_sh
    monkeypatch.setenv("DRY_RUN", "true")
    _write_work("drift.json", _base_drift(level=2))
    _write_work("roster-report.json", {"pending_state": None})
    _write_work("source-status.json", {"cs2settings": "ok"})
    _write_work("metrics.json", {"aggregate": {"snapshot_date": "2026-08-01"}, "panel": {}})
    assert actions_daily.main() == 0
    assert not [c for c in calls if c[0] == "gh"]


def test_level1_issue_only(_patch_sh):
    state, calls = _patch_sh
    _write_work("drift.json", _base_drift(level=1))
    _write_work("roster-report.json", {"pending_state": None})
    _write_work("source-status.json", {"cs2settings": "ok"})
    _write_work("metrics.json", {"aggregate": {}, "panel": {}})
    assert actions_daily.main() == 0
    gh_calls = [c for c in calls if c[0] == "gh" and c[1] == "issue"]
    assert gh_calls, "Level 1 must open an issue"
    assert "pr" not in " ".join(" ".join(c) for c in calls).lower() or \
        not [c for c in calls if c[0] == "gh" and c[1] == "pr"]


def test_level2_stable_creates_candidate_pr(_patch_sh):
    state, calls = _patch_sh
    _write_work("drift.json", _base_drift(level=2))
    _write_work("roster-report.json", {"pending_state": None})
    _write_work("source-status.json", {"cs2settings": "ok"})
    _write_work("metrics.json", {"aggregate": {"snapshot_date": "2026-08-01"}, "panel": {}})
    assert actions_daily.main() == 0
    pr_calls = [c for c in calls if c[0] == "gh" and c[1] == "pr" and c[2] == "create"]
    assert pr_calls, "Level 2 stable must create a candidate PR"


def test_level2_suppressed_no_headline_pr(_patch_sh):
    state, calls = _patch_sh
    _write_work("drift.json", _base_drift(level=2, suppressed=True))
    _write_work("roster-report.json", {"pending_state": None})
    _write_work("source-status.json", {"cs2settings": "ok"})
    _write_work("metrics.json", {"aggregate": {}, "panel": {}})
    assert actions_daily.main() == 0
    pr_calls = [c for c in calls if c[0] == "gh" and c[1] == "pr" and c[2] == "create"]
    assert not pr_calls, "suppressed headline must not create a headline PR"


def test_series_incompatible_no_headline_pr(_patch_sh):
    state, calls = _patch_sh
    _write_work("drift.json", _base_drift(level=2, series_ok=False))
    _write_work("roster-report.json", {"pending_state": None})
    _write_work("source-status.json", {"cs2settings": "ok"})
    _write_work("metrics.json", {"aggregate": {}, "panel": {}})
    assert actions_daily.main() == 0
    pr_calls = [c for c in calls if c[0] == "gh" and c[1] == "pr" and c[2] == "create"]
    assert not pr_calls


def test_primary_source_failure_issue_path(monkeypatch, _patch_sh):
    """Source failure: decision step must run and raise the issue; script fails."""
    state, calls = _patch_sh
    monkeypatch.setenv("PIPELINE_OUTCOME", "failure")
    _write_work("drift.json", _base_drift())
    _write_work("roster-report.json", {"pending_state": None})
    _write_work("source-status.json", {"cs2settings": "error: timeout"})
    _write_work("metrics.json", {"aggregate": {}, "panel": {}})
    rc = actions_daily.main()
    assert rc != 0, "workflow must stay red on pipeline failure"
    issue_calls = [c for c in calls if c[0] == "gh" and c[1] == "issue" and c[2] == "create"]
    assert issue_calls, "source-health issue must be raised on failure"


def test_issue_dedup_existing_open_issue_updated(monkeypatch, _patch_sh):
    state, calls = _patch_sh
    state["issues"].append({"number": "7", "open": True})  # pre-existing open issue
    monkeypatch.setenv("PIPELINE_OUTCOME", "failure")
    _write_work("drift.json", _base_drift())
    _write_work("roster-report.json", {"pending_state": None})
    _write_work("source-status.json", {"cs2settings": "error"})
    _write_work("metrics.json", {"aggregate": {}, "panel": {}})
    actions_daily.main()
    creates = [c for c in calls if c[0] == "gh" and c[1] == "issue" and c[2] == "create"]
    comments = [c for c in calls if c[0] == "gh" and c[1] == "issue" and c[2] == "comment"]
    assert not creates, "must not create a second issue"
    assert comments, "must update the existing open issue"


def test_existing_pr_branch_reused(monkeypatch, _patch_sh):
    """Existing automation PR: its REAL head branch is reused; no new create."""
    state, calls = _patch_sh
    state["prs"].append({"number": "3", "open": True,
                         "head": "automation/settings-update-20260801"})
    _write_work("drift.json", _base_drift(level=2))
    _write_work("roster-report.json", {"pending_state": None})
    _write_work("source-status.json", {"cs2settings": "ok"})
    _write_work("metrics.json", {"aggregate": {"snapshot_date": "2026-08-01"}, "panel": {}})
    assert actions_daily.main() == 0
    creates = [c for c in calls if c[0] == "gh" and c[1] == "pr" and c[2] == "create"]
    edits = [c for c in calls if c[0] == "gh" and c[1] == "pr" and c[2] == "edit"]
    fetches = [c for c in calls if c[0] == "git" and c[1] == "fetch"]
    assert not creates, "must not create a second PR"
    assert edits, "must update the existing PR body"
    assert fetches, "must fetch the existing PR branch"
    assert not any("--force" in c for c in calls), "must not force push"


def test_missing_label_does_not_block_pr(_patch_sh):
    """PR creation must not depend on the automated-data-update label."""
    state, calls = _patch_sh
    _write_work("drift.json", _base_drift(level=2))
    _write_work("roster-report.json", {"pending_state": None})
    _write_work("source-status.json", {"cs2settings": "ok"})
    _write_work("metrics.json", {"aggregate": {}, "panel": {}})
    assert actions_daily.main() == 0
    pr_calls = [c for c in calls if c[0] == "gh" and c[1] == "pr" and c[2] == "create"]
    assert pr_calls
    assert not any("--label" in c for c in pr_calls), "label must not be required"
