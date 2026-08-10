"""ProSettings.net adapter — compatibility / user-triggered reconciliation.

NOT enabled for scheduled collection (enabled_for_schedule=False): public
automation should not default to mirroring third-party row-level data.
Used only for local, user-triggered reconciliation and existing-workflow
migration.

Parsing logic is a minimal migration of notebooks/v1/01_data_collection.ipynb:
- list page: HTML table rows (th/td) with a header row containing "Player"/"DPI";
- detail page: label-value sections parsed semantically.

No raw HTML is saved and crawl results are never committed.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

from .base import AccessPolicy, ParsedPlayer, SourceError

BASE_URL = "https://prosettings.net"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"}


class ProSettingsSource:
    name = "prosettings"
    enabled_for_schedule = False

    def __init__(self, base_url: str = BASE_URL, timeout: int = 20) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(HEADERS)

    def check_access_policy(self) -> AccessPolicy:
        robots = self._get_text(f"{self.base_url}/robots.txt")
        blocked = re.search(r"Disallow:\s*/(players|lists)", robots)
        return AccessPolicy(
            robots_allows=not blocked,
            accessible=True,
            terms_url=f"{self.base_url}/terms/",
            notes="robots.txt blocks wp-admin/wp-json/search; player/list pages are allowed",
        )

    def list_players(self, player_list_url: Optional[str] = None) -> list[dict]:
        """Parse the /lists/cs2/ table (v1 notebook Cell 4 + 5 logic)."""
        url = player_list_url or f"{self.base_url}/lists/cs2/"
        html = self._get_text(url)
        soup = BeautifulSoup(html, "html.parser")
        players: list[dict] = []
        for row in soup.find_all("tr"):
            cells = row.find_all(["th", "td"])
            texts = [c.get_text(separator=" ", strip=True) for c in cells]
            if not texts:
                continue
            if "Player" in texts and "DPI" in texts:
                continue  # header row
            for link in row.find_all("a"):
                href = link.get("href") or ""
                if "players/" not in href:
                    continue
                name = link.get_text(strip=True)
                if name:
                    source_id = href.rstrip("/").split("/")[-1]
                    players.append({"source_id": source_id, "name": name, "url": href})
                    break
        return players

    def fetch_player(self, source_id: str) -> ParsedPlayer:
        url = f"{self.base_url}/players/{source_id}/"
        html = self._get_text(url)
        fields: dict[str, Any] = {}
        soup = BeautifulSoup(html, "html.parser")

        # detail-page semantic label/value pairs (v1 Cell 6/7 style, no CSS anchors)
        for label in soup.find_all(["h2", "h3", "dt", "th"]):
            text = label.get_text(" ", strip=True)
            if not text or len(text) > 60:
                continue
            value = label.find_next(["p", "dd", "td"])
            if value:
                fields[text.lower()] = value.get_text(" ", strip=True)

        return ParsedPlayer(
            source=self.name,
            source_id=source_id,
            name=source_id,
            source_url=url,
            retrieved_at=date.today().isoformat(),
            steam_id=None,
            fields=fields,
        )

    def normalize(self, parsed: ParsedPlayer) -> dict[str, Any]:
        return parsed.fields

    def _get_text(self, url: str) -> str:
        try:
            resp = self._session.get(url, timeout=self.timeout)
        except requests.RequestException as exc:
            raise SourceError(f"prosettings: request failed for {url}: {exc}") from exc
        if resp.status_code != 200:
            raise SourceError(f"prosettings: HTTP {resp.status_code} for {url}")
        return resp.text
