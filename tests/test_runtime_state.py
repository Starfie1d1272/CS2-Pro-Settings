"""Runtime state: warmup, confirmation window, cache miss safety, panel."""
import json
from pathlib import Path

import pytest

from cs2_pro_settings import runtime_state
from cs2_pro_settings.models import NormalizedPlayerSettings
from cs2_pro_settings.roster import compute_roster_report, update_pending_state


def p(player_id, **kw):
    base = dict(player_id=player_id, canonical_name=player_id)
    base.update(kw)
    return NormalizedPlayerSettings(**base)


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv(runtime_state.STATE_DIR_ENV, str(tmp_path))
    yield tmp_path


def test_warmup_no_previous_does_not_false_diff(isolated_state):
    """A: no runtime state -> warmup, no roster issue, no Level 2."""
    from cs2_pro_settings.cli import step_roster

    roster = {"vitality": ["steam:1", "steam:2"]}
    info = step_roster(roster, "2026-08-01")
    assert info["status"] == "warmup"
    assert info["turnover_rate"] is None
    assert info["has_changes"] is False  # NOT 'all players added'
    report = json.loads(Path("work/roster-report.json").read_text(encoding="utf-8"))
    assert report["has_comparable_previous"] is False
    assert report["status"] == "warmup"


def test_pending_then_confirmed_across_runs(isolated_state):
    """B-E: run1 saves state; run2 diff -> pending; run3 same diff -> confirmed."""
    from cs2_pro_settings.cli import _persist_runtime_state, step_roster

    # run1: warmup, then persist
    roster1 = {"vitality": ["steam:1", "steam:2", "steam:3"]}
    info1 = step_roster(roster1, "2026-08-01")
    metrics1 = {"aggregate": {"snapshot_date": "2026-08-01"},
                "panel": {"player_ids": ["steam:1", "steam:2", "steam:3"],
                          "players": {f"steam:{i}": {"dpi": 800.0, "edpi": 800.0,
                                                     "resolution": "1280x960", "polling_rate": 1000}
                                      for i in (1, 2, 3)}}}
    _persist_runtime_state(roster1, metrics1, info1.get("pending_state"))
    assert runtime_state.load_state("roster-previous.json") is not None
    assert runtime_state.load_state("previous-panel.json") is not None

    # run2: one out, one in -> pending (first observation)
    roster2 = {"vitality": ["steam:1", "steam:2", "steam:4"]}
    info2 = step_roster(roster2, "2026-08-02")
    assert info2["status"] == "compared"
    assert info2["has_changes"] is True
    assert info2["pending_state"]["status"] == "pending"
    _persist_runtime_state(roster2, metrics1, info2.get("pending_state"))

    # run3: identical diff -> confirmed
    info3 = step_roster(roster2, "2026-08-03")
    assert info3["pending_state"]["status"] == "confirmed"
    assert info3["pending_state"]["first_observed_at"] == "2026-08-02"


def test_change_disappears_clears_pending(isolated_state):
    from cs2_pro_settings.cli import _persist_runtime_state, step_roster

    roster1 = {"vitality": ["steam:1", "steam:2"]}
    info1 = step_roster(roster1, "2026-08-01")
    metrics = {"aggregate": {"snapshot_date": "2026-08-01"},
               "panel": {"player_ids": [], "players": {}}}
    _persist_runtime_state(roster1, metrics, info1.get("pending_state"))
    roster2 = {"vitality": ["steam:1", "steam:2", "steam:3"]}
    info2 = step_roster(roster2, "2026-08-02")
    _persist_runtime_state(roster2, metrics, info2.get("pending_state"))
    st = runtime_state.load_state("roster-pending.json")
    assert st is not None and st["status"] == "pending"
    # next run: back to original roster -> pending cleared
    info3 = step_roster(roster1, "2026-08-03")
    assert info3["pending_state"] is None
    _persist_runtime_state(roster1, metrics, info3.get("pending_state"))
    assert runtime_state.load_state("roster-pending.json") is None


def test_cache_miss_again_safe_warmup(isolated_state):
    """F: state missing again -> safe warmup, not false confirmed."""
    from cs2_pro_settings.cli import _persist_runtime_state, step_roster

    roster = {"vitality": ["steam:1"]}
    info = step_roster(roster, "2026-08-01")
    metrics = {"aggregate": {"snapshot_date": "2026-08-01"},
               "panel": {"player_ids": ["steam:1"], "players": {}}}
    _persist_runtime_state(roster, metrics, info.get("pending_state"))
    # simulate cache eviction
    runtime_state.clear_state("roster-previous.json")
    runtime_state.clear_state("roster-pending.json")
    info2 = step_roster(roster, "2026-08-05")
    assert info2["status"] == "warmup"
    assert info2["has_changes"] is False
    assert info2["pending_state"] is None


def test_previous_panel_minimal_fields():
    metrics = {
        "aggregate": {"snapshot_date": "2026-08-01"},
        "panel": {
            "player_ids": ["steam:1"],
            "players": {"steam:1": {"dpi": 800.0, "edpi": 800.0, "resolution": "1280x960",
                                    "polling_rate": 1000, "team": "vitality",
                                    "canonical_name": "Player"}},
        },
    }
    panel = runtime_state.build_previous_panel(metrics)
    # only matched-panel fields are kept
    assert set(panel["players"]["steam:1"].keys()) == {"dpi", "edpi", "resolution", "polling_rate"}


def test_compare_panels_matched():
    prev = {"player_ids": ["steam:1", "steam:2"],
            "players": {"steam:1": {"dpi": 800.0}, "steam:2": {"dpi": 400.0}}}
    cur = {"player_ids": ["steam:1", "steam:3"],
           "players": {"steam:1": {"dpi": 400.0}, "steam:3": {"dpi": 800.0}}}
    res = runtime_state.compare_panels(prev, cur)
    assert res["matched_count"] == 1
    assert res["per_field"]["dpi"] == {
        "changed": 1, "compared": 1, "missing_transition": 0,
        "missing_to_value": 0, "value_to_missing": 0}


def test_compare_panels_missing_to_value_is_not_a_change():
    """10: missing->value transition is a completeness change, not a settings change."""
    prev = {"player_ids": ["steam:1", "steam:2"],
            "players": {"steam:1": {"dpi": None}, "steam:2": {"dpi": 400.0}}}
    cur = {"player_ids": ["steam:1", "steam:2"],
           "players": {"steam:1": {"dpi": 800.0}, "steam:2": {"dpi": 400.0}}}
    res = runtime_state.compare_panels(prev, cur)
    dpi = res["per_field"]["dpi"]
    assert dpi["compared"] == 1      # only steam:2 has both-time values
    assert dpi["changed"] == 0       # None->800 is NOT a settings change
    assert dpi["missing_to_value"] == 1
    assert dpi["missing_transition"] == 1


def test_compare_panels_value_to_missing_is_a_transition():
    """P: value->None is also a missing transition, not a settings change."""
    prev = {"player_ids": ["steam:1", "steam:2"],
            "players": {"steam:1": {"dpi": 800.0}, "steam:2": {"dpi": 400.0}}}
    cur = {"player_ids": ["steam:1", "steam:2"],
           "players": {"steam:1": {"dpi": None}, "steam:2": {"dpi": 400.0}}}
    res = runtime_state.compare_panels(prev, cur)
    dpi = res["per_field"]["dpi"]
    assert dpi["compared"] == 1      # only steam:2 has both-time values
    assert dpi["changed"] == 0       # 800->None is NOT a settings change
    assert dpi["value_to_missing"] == 1
    assert dpi["missing_transition"] == 1
