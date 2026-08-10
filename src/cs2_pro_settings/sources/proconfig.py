"""Pro Config adapter — secondary editorial cross-check (DISABLED by default).

URL: https://proconfig.net  (the previous `.gg` probe was incorrect and is
superseded — see docs/source-audit/proconfig.md).

Policy: robots.txt `Allow: /` (only /downloads/, /product/, /search-index.json
disallowed); an editorial-process page documents a "Verified Config & Gear"
standard; normal GET returns 200 without a bot challenge.

Role: secondary editorial cross-check ONLY. No full-site enumeration, never
defines the cohort, never replaces the primary source, no high-frequency
scheduled crawling.

Parsing: semantic label-value pairs (<dt>/<dd>) plus JSON-LD (Person,
ProfilePage.lastReviewed, FAQPage). CSS classes are not parser anchors.

If a field is not reliably available on the page, it is left missing — never
guessed.
"""
from __future__ import annotations

import json
import re
from datetime import date
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

from ..normalize import color_category, to_hz, to_int
from .base import AccessPolicy, ParsedPlayer, SourceError

BASE_URL = "https://proconfig.net"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"}

# dt/dd label -> normalized field name (adapter-level mapping; value parsing
# still happens in normalize.py via normalize_field)
_LABEL_MAP = {
    "DPI": "dpi",
    "eDPI": "edpi",
    "Sensitivity": "sensitivity",
    "Zoom Sensitivity": "zoom_sensitivity",
    "Polling Rate": "polling_rate",
    "Resolution": "resolution",
    "Aspect Ratio": "aspect_ratio",
    "Scaling Mode": "scaling_mode",
    "Refresh Rate": "refresh_rate",
    "Brightness": "brightness",
    "Vertical Sync": "vsync",
    "Style": "crosshair_style",
    "Size": "crosshair_size",
    "Thickness": "crosshair_thickness",
    "Gap": "crosshair_gap",
    "Outline": "crosshair_outline",
    "Color": "crosshair_color",
}


def _rgb_to_color(v: str) -> Optional[str]:
    """'255, 255, 255' -> 'Custom'; plain color names -> category."""
    if re.search(r"\d+\s*,\s*\d+\s*,\s*\d+", v):
        return "Custom"
    return color_category(v)


class ProConfigSource:
    name = "proconfig"
    enabled_for_schedule = False  # secondary; never scheduled

    def __init__(self, base_url: str = BASE_URL, timeout: int = 20) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(HEADERS)

    def check_access_policy(self) -> AccessPolicy:
        robots = self._get_text(f"{self.base_url}/robots.txt")
        allowed = "disallow: /players" not in robots.lower() and "disallow: /cs2" not in robots.lower()
        try:
            resp = self._session.get(f"{self.base_url}/cs2/", timeout=self.timeout)
            ok = resp.status_code == 200 and "proconfig" in resp.text.lower()
        except requests.RequestException as exc:
            raise SourceError(f"proconfig: access check failed: {exc}") from exc
        return AccessPolicy(
            robots_allows=allowed,
            accessible=ok,
            terms_url=f"{self.base_url}/editorial-process/",
            notes="robots.txt Allow / (blocks /downloads/ /product/ /search-index.json); "
                  "editorial-process page documents verified-data standard",
        )

    def fetch_player(self, source_id: str) -> ParsedPlayer:
        url = f"{self.base_url}/cs2/{source_id}/"
        html = self._get_text(url)
        soup = BeautifulSoup(html, "html.parser")

        # --- label/value pairs (semantic, no CSS anchors) ---
        pairs: dict[str, str] = {}
        for dl in soup.find_all("dl"):
            for div in dl.find_all("div", recursive=False):
                dt = div.find("dt")
                dd = div.find("dd")
                if dt and dd:
                    key = dt.get_text(" ", strip=True)
                    val = dd.get_text(" ", strip=True)
                    if key:
                        pairs[key] = val

        # --- JSON-LD ---
        person = {}
        profile = {}
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                obj = json.loads(s.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(obj, dict):
                continue
            t = obj.get("@type")
            if t == "Person":
                person = obj
            elif t == "ProfilePage":
                profile = obj

        steam_id = None
        m = re.search(r"steamcommunity\.com/profiles/(\d{15,17})", html)
        if m:
            steam_id = m.group(1)

        fields: dict[str, Any] = {}
        for label, attr in _LABEL_MAP.items():
            if label not in pairs:
                continue
            value: Any = pairs[label]
            if label == "Color":
                value = _rgb_to_color(value)
            elif label == "Style":
                value = re.sub(r"^\d+\s*\(([^)]+)\)$", r"\1", value)  # "1 (Classic Static)" -> "Classic Static"
            fields[attr] = value

        team = None
        mo = person.get("memberOf") or {}
        if isinstance(mo, dict):
            team = mo.get("name")

        return ParsedPlayer(
            source=self.name,
            source_id=source_id,
            name=person.get("alternateName") or source_id,
            source_url=url,
            retrieved_at=date.today().isoformat(),
            steam_id=steam_id,
            team=team,
            role=None,
            country=person.get("nationality"),
            source_updated_at=profile.get("lastReviewed") or profile.get("dateModified"),
            fields=fields,
        )

    def normalize(self, parsed: ParsedPlayer) -> dict[str, Any]:
        return parsed.fields

    def _get_text(self, url: str) -> str:
        try:
            resp = self._session.get(url, timeout=self.timeout)
        except requests.RequestException as exc:
            raise SourceError(f"proconfig: request failed for {url}: {exc}") from exc
        if resp.status_code != 200:
            raise SourceError(f"proconfig: HTTP {resp.status_code} for {url}")
        return resp.text
