"""ProConfig adapter tests — fixtures only, no network."""
from cs2_pro_settings.sources.proconfig import ProConfigSource, _rgb_to_color


def read_fixture(fixture_dir, name):
    return (fixture_dir / f"{name}.html").read_text(encoding="utf-8")


def _source_for(html):
    src = ProConfigSource()

    def fake_get(url):
        return html

    src._get_text = fake_get  # type: ignore[method-assign]
    return src


def test_fixture_a_full_player(proconfig_fixture_dir):
    html = read_fixture(proconfig_fixture_dir, "player-a")
    parsed = _source_for(html).fetch_player("player-a")
    assert parsed.name == "PlayerA"
    assert parsed.team == "Example FC"
    assert parsed.country == "Germany"
    assert parsed.steam_id == "76561198000000001"
    assert parsed.source_updated_at == "2026-07-01"
    assert parsed.fields["dpi"] == "800"
    assert parsed.fields["sensitivity"] == "1.25"
    assert parsed.fields["edpi"] == "1000"
    assert parsed.fields["resolution"] == "1280x960"
    assert parsed.fields["crosshair_color"] == "Custom"
    assert parsed.fields["crosshair_style"] == "Classic Static"
    assert parsed.fields["polling_rate"] == "1000 Hz"


def test_fixture_b_missing_fields_legal(proconfig_fixture_dir):
    html = read_fixture(proconfig_fixture_dir, "player-b")
    parsed = _source_for(html).fetch_player("player-b")
    assert parsed.fields["dpi"] == "400"
    assert "resolution" not in parsed.fields
    assert "crosshair_style" not in parsed.fields  # missing is legal, not guessed


def test_rgb_to_color():
    assert _rgb_to_color("255, 255, 255") == "Custom"
    assert _rgb_to_color("0, 255, 145") == "Custom"
    assert _rgb_to_color("Cyan") == "Cyan"
    assert _rgb_to_color("Green") == "Green"


def test_base_url_is_dot_net():
    from cs2_pro_settings.sources.proconfig import BASE_URL
    assert BASE_URL == "https://proconfig.net"
    assert "proconfig.gg" not in BASE_URL
