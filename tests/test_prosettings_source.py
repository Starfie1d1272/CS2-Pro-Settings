"""ProSettings adapter: local reconciliation + SteamID parsing."""
import re
from datetime import date
from typing import Any, Optional

from bs4 import BeautifulSoup

from cs2_pro_settings.sources.base import AccessPolicy, ParsedPlayer
from cs2_pro_settings.sources.prosettings import ProSettingsSource


def _parse_fixture(src: ProSettingsSource, source_id: str, html: str) -> ParsedPlayer:
    orig = src._get_text

    def fake_get(url: str) -> str:
        return html

    src._get_text = fake_get  # type: ignore[method-assign]
    try:
        return src.fetch_player(source_id)
    finally:
        src._get_text = orig  # type: ignore[method-assign]


FIXTURES = None  # replaced by conftest fixture dir


def test_prosettings_numeric_steam_profile_is_identity(prosettings_fixture_dir):
    src = ProSettingsSource(base_url="https://prosettings.net")
    html = (prosettings_fixture_dir / "zywoo.html").read_text(encoding="utf-8")
    parsed = _parse_fixture(src, "zywoo", html)
    assert parsed.steam_id == "76561198113666193"
    assert parsed.fields.get("dpi") == "800"


def test_prosettings_vanity_steam_link_is_not_identity(prosettings_fixture_dir):
    src = ProSettingsSource(base_url="https://prosettings.net")
    html = (prosettings_fixture_dir / "donk.html").read_text(encoding="utf-8")
    parsed = _parse_fixture(src, "donk", html)
    assert parsed.steam_id is None  # /id/<vanity> is not numeric identity


def test_prosettings_capabilities_declared_in_config(repo_root):
    import yaml

    cfg = yaml.safe_load((repo_root / "config" / "sources.yaml").read_text())
    ps = cfg["sources"]["prosettings"]
    assert ps["enabled_for_schedule"] is False  # local-only policy unchanged
    caps = ps["capabilities"]
    assert caps["player_settings"] is True
    assert caps["roster_discovery"] is False
