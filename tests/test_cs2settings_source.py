"""CS2Settings source adapter tests — fixtures only, no network."""
import pytest

from cs2_pro_settings.sources.base import SourceError
from cs2_pro_settings.sources.cs2settings import (
    CS2SettingsSource,
    _clean_steam_id,
    _extract_player_blob,
    _extract_players_blob,
)


def read_fixture(fixture_dir, name):
    return (fixture_dir / f"{name}.html").read_text(encoding="utf-8")


def test_fixture_a_full_player(cs2settings_fixture_dir):
    html = read_fixture(cs2settings_fixture_dir, "player-a")
    blob = _extract_player_blob(html)
    assert blob["displayName"] == "PlayerA"
    assert _clean_steam_id(blob["steamId"]) == "76561198000000001"
    assert blob["mouse"]["dpi"] == 800
    assert blob["crosshair"]["dot"] is False
    assert blob["videoSettings"]["resolution"] == "1280x960"
    assert blob["lastVerified"] == "2026-07-01"


def test_fixture_a_parsed_player(cs2settings_fixture_dir):
    src = CS2SettingsSource()
    html = read_fixture(cs2settings_fixture_dir, "player-a")
    parsed = src._blob_to_parsed("player-a", "https://cs2settings.com/players/player-a",
                                 _extract_player_blob(html))
    assert parsed.steam_id == "76561198000000001"
    assert parsed.team == "examplefc"
    assert parsed.source_updated_at == "2026-07-01"
    assert parsed.fields["dpi"] == 800
    assert parsed.fields["crosshair_color"] == "Custom"  # color code 5 -> Custom
    assert parsed.fields["viewmodel_fov"] == 68


def test_fixture_b_missing_fields_legal(cs2settings_fixture_dir):
    html = read_fixture(cs2settings_fixture_dir, "player-b")
    blob = _extract_player_blob(html)
    assert blob["steamId"]
    assert "crosshair" not in blob  # missing is legal
    assert "videoSettings" not in blob
    src = CS2SettingsSource()
    parsed = src._blob_to_parsed("player-b", "u", blob)
    assert parsed.fields["dpi"] == 400
    assert "crosshair_color" not in parsed.fields


def test_fixture_c_tricky_text(cs2settings_fixture_dir):
    """Apostrophes, https:// URLs, escaped quotes, braces, backslashes, .7."""
    html = read_fixture(cs2settings_fixture_dir, "player-tricky")
    blob = _extract_player_blob(html)
    assert blob["displayName"] == "PlayerTricky"
    assert blob["realName"] == "T. \"Tricky\" O'Neil"
    assert blob["mapSettings"]["radarZoom"] == 0.65  # .65 shorthand
    content = blob["content"]
    assert "it's tricky" in content
    assert "https://example.com/players/tricky" in content
    assert "hello" in content
    assert "C:\\temp\\config" in content
    assert blob["crosshair"]["color"] == 5
    assert blob["mouse"]["pollingRate"] == 8000


def test_no_blob_raises(cs2settings_fixture_dir):
    with pytest.raises(SourceError):
        _extract_player_blob("<html><body><p>no data here</p></body></html>")


def test_unbalanced_blob_raises(cs2settings_fixture_dir):
    html = "<html><body><script>data:{player:{steamId:1,mouse:{dpi:400</script></body></html>"
    with pytest.raises(SourceError):
        _extract_player_blob(html)


def test_players_list_blob():
    html = ("<html><body><script>kit.start(a, e, {data:[{type:\"data\",data:{players:["
            "{id:\"zywoo\",displayName:\"ZywOo\",teamName:\"Vitality\"},"
            "{id:\"donk\",displayName:\"donk\",teamName:\"Spirit\"}]}}]});</script></body></html>")
    players = _extract_players_blob(html)
    assert [p["id"] for p in players] == ["zywoo", "donk"]
    assert players[0]["teamName"] == "Vitality"


def test_steam_id_cleaning():
    assert _clean_steam_id("76561198113666193") == "76561198113666193"
    assert _clean_steam_id("https://steamcommunity.com/profiles/76561198113666193") == "76561198113666193"
    assert _clean_steam_id(None) is None
