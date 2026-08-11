"""Player identity rules."""
from cs2_pro_settings.identity import IdentityIndex, canonical_player_id


def test_steam_id_preferred_over_source_id():
    pid = canonical_player_id("76561198000000001", "cs2settings", "zywoo")
    assert pid == "steam:76561198000000001"


def test_no_steam_id_uses_source_stable_id():
    pid = canonical_player_id(None, "cs2settings", "zywoo")
    assert pid == "source:cs2settings:zywoo"


def test_nickname_never_used_as_id():
    assert canonical_player_id(None, "prosettings", "ZywOo").startswith("source:")
    tail = canonical_player_id("1", "x", "y").split(":")[-1]
    assert tail != "y"  # bare nickname must never become the permanent id


def test_same_steam_id_changed_nickname_same_player():
    idx = IdentityIndex()
    a = idx.register(source="cs2settings", source_id="zywoo", name="ZywOo", steam_id="76561198000000001")
    b = idx.register(source="cs2settings", source_id="zywoo", name="Zyw0o", steam_id="76561198000000001")
    assert a.player_id == b.player_id
    assert idx.player_count() == 1


def test_same_nickname_different_steam_id_collision_flag():
    idx = IdentityIndex()
    a = idx.register(source="cs2settings", source_id="player-x", name="PlayerX", steam_id="76561198000000001")
    b = idx.register(source="cs2settings", source_id="player-x", name="PlayerX", steam_id="76561198000000002")
    # same stable source identity is NOT split, but the SteamID change is surfaced
    assert a.player_id == b.player_id
    assert any(p["type"] == "steam_id_change" for p in idx.identity_problems)


def test_cross_source_same_steam_links():
    idx = IdentityIndex()
    a = idx.register(source="cs2settings", source_id="zywoo", name="ZywOo", steam_id="76561198000000001")
    b = idx.register(source="proconfig", source_id="zywoo", name="ZywOo", steam_id="76561198000000001")
    assert a.player_id == b.player_id
    assert b.source_ids == {"cs2settings": "zywoo", "proconfig": "zywoo"}


def test_same_nickname_without_steam_distinct_players():
    idx = IdentityIndex()
    a = idx.register(source="cs2settings", source_id="a", name="Nick")
    b = idx.register(source="cs2settings", source_id="b", name="Nick")
    assert a.player_id != b.player_id
    assert idx.player_count() == 2
