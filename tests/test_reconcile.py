"""Reconciliation: no silent overwrite, priority from config, disabled skip."""
from cs2_pro_settings.models import SourceObservation
from cs2_pro_settings.reconcile import reconcile

PRIORITY = {
    "dpi": ["cs2settings", "proconfig", "prosettings"],
    "crosshair": ["cs2settings", "proconfig", "prosettings"],
    "gear": ["cs2settings", "prosettings", "proconfig"],
}


def obs(player, field, value, source, retrieved="2026-08-01"):
    return SourceObservation(
        player_id=player,
        field=field,
        value=value,
        source=source,
        source_url=f"https://{source}/p/{player}",
        retrieved_at=retrieved,
        raw_label=str(value),
    )


def test_conflict_not_silently_overwritten():
    observations = [
        obs("steam:1", "dpi", 800.0, "cs2settings"),
        obs("steam:1", "dpi", 400.0, "prosettings"),
    ]
    result = reconcile(observations, PRIORITY, {"cs2settings", "prosettings"})
    assert len(result.conflicts) == 1
    c = result.conflicts[0]
    assert c["player_id"] == "steam:1"
    assert c["field"] == "dpi"
    assert {c["source_a"], c["source_b"]} == {"cs2settings", "prosettings"}
    # primary from priority config, conflict recorded, not overwritten silently
    assert result.players["steam:1"].dpi == 800.0
    assert result.players["steam:1"].provenance["dpi"]["source"] == "cs2settings"


def test_same_value_no_conflict():
    observations = [
        obs("steam:1", "dpi", 800.0, "cs2settings"),
        obs("steam:1", "dpi", 800.0, "prosettings"),
    ]
    result = reconcile(observations, PRIORITY, {"cs2settings", "prosettings"})
    assert result.conflicts == []
    assert result.players["steam:1"].dpi == 800.0


def test_disabled_source_skipped():
    observations = [
        obs("steam:1", "dpi", 800.0, "cs2settings"),
        obs("steam:1", "dpi", 1600.0, "proconfig"),  # disabled
    ]
    result = reconcile(observations, PRIORITY, {"cs2settings"})
    assert result.conflicts == []
    assert result.players["steam:1"].dpi == 800.0
    assert result.players["steam:1"].provenance["dpi"]["source"] == "cs2settings"


def test_priority_respects_config_order():
    observations = [
        obs("steam:1", "crosshair_color", "Cyan", "cs2settings"),
        obs("steam:1", "crosshair_color", "Green", "prosettings"),
        obs("steam:1", "crosshair_color", "Yellow", "proconfig"),
    ]
    result = reconcile(observations, PRIORITY, {"cs2settings", "prosettings", "proconfig"})
    assert result.players["steam:1"].crosshair_color == "Cyan"
    # three pairwise conflicts recorded (all sources disagree)
    assert len(result.conflicts) == 3


def test_missing_field_absent():
    observations = [obs("steam:1", "dpi", 800.0, "cs2settings")]
    result = reconcile(observations, PRIORITY, {"cs2settings"})
    p = result.players["steam:1"]
    assert p.dpi == 800.0
    assert p.crosshair_color is None  # missing is legal
