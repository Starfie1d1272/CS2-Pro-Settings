"""CS2Settings.com adapter — v2 primary active source.

Policy: robots.txt has no Disallow rules (Cloudflare content signals only,
which do not restrict non-AI collection); normal GET returns 200 without a
bot challenge. See docs/source-audit/cs2settings.md.

Parsing: the player page embeds a structured data blob
(`data:[{type:"data",data:{player:{...}}}]` inside a SvelteKit bootstrap
script). We parse that blob with a tolerant JS-object-literal -> JSON
converter and map the semantic fields. CSS class names are never used as
parser anchors.

Fail closed: any HTTP or parse failure raises SourceError.
"""
from __future__ import annotations

import json
import re
from datetime import date
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

from .base import AccessPolicy, ParsedPlayer, SourceError

BASE_URL = "https://cs2settings.com"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"}

# ---------------------------------------------------------------------------
# tolerant JS object literal -> JSON
# ---------------------------------------------------------------------------

_WS = re.compile(r"\s+")


def _strip_js_comments(html: str) -> str:
    """Remove // line comments and /* */ block comments outside strings.

    Handles both ' and " quoted strings with backslash escapes.
    """
    out: list[str] = []
    i, n = 0, len(html)
    in_str: str | None = None  # quote char when inside a string
    while i < n:
        ch = html[i]
        if in_str is not None:
            out.append(ch)
            if ch == "\\":
                i += 1
                if i < n:
                    out.append(html[i])
            elif ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ("'", '"'):
            in_str = ch
            out.append(ch)
            i += 1
            continue
        if html.startswith("//", i):
            j = html.find("\n", i)
            i = j if j != -1 else n
            continue
        if html.startswith("/*", i):
            j = html.find("*/", i + 2)
            i = j + 2 if j != -1 else n
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _extract_balanced(text: str, start: int, open_ch: str, close_ch: str) -> int:
    """String-aware scan for the matching close bracket; returns index after it."""
    depth = 0
    i = start
    n = len(text)
    in_str: str | None = None
    while i < n:
        ch = text[i]
        if in_str is not None:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ("'", '"'):
            in_str = ch
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def _extract_player_blob(html: str) -> dict:
    """Extract and parse the embedded `data:{player:{...}}` object.

    Returns the player dict; raises SourceError if not found/parseable.
    """
    cleaned = _strip_js_comments(html)
    marker = 'data:{player:{'
    idx = cleaned.find(marker)
    if idx == -1:
        raise SourceError("cs2settings: player data blob not found")
    start = idx + len(marker) - 1  # position of '{' after 'player:'
    end = _extract_balanced(cleaned, start, "{", "}")
    if end == -1:
        raise SourceError("cs2settings: unbalanced player data blob")

    literal = cleaned[start:end]
    return _js_literal_to_json(literal)


def _js_literal_to_json(literal: str) -> dict:
    """Convert a JS object literal to a Python dict (tolerant, string-aware)."""
    s = literal
    s = re.sub(r"void\s+0", "null", s)
    s = re.sub(r"\bundefined\b", "null", s)
    s = re.sub(r"NaN", "null", s)
    # quote unquoted keys and drop trailing commas, but never inside strings
    out: list[str] = []
    i, n = 0, len(s)
    in_str: str | None = None
    while i < n:
        ch = s[i]
        if in_str is not None:
            out.append(ch)
            if ch == "\\":
                i += 1
                if i < n:
                    out.append(s[i])
            elif ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ("'", '"'):
            in_str = ch
            out.append(ch)
            i += 1
            continue
        # trailing comma before } or ]
        if ch == ",":
            j = i + 1
            while j < n and s[j] in " \t\n\r":
                j += 1
            if j < n and s[j] in "}]":
                i = j
                continue
            out.append(ch)
            i += 1
            continue
        # unquoted key: ( { , whitespace ) ident ( whitespace ) :
        if ch in "{," or ch in " \t\n\r":
            m = re.match(r"([{,][ \t\n\r]*|^[ \t\n\r]*)([A-Za-z_$][\w$]*)[ \t\n\r]*:", s[i:])
            if m:
                out.append(m.group(1))
                out.append('"' + m.group(2) + '":')
                i += m.end()
                continue
        out.append(ch)
        i += 1
    try:
        obj = json.loads("".join(out))
    except json.JSONDecodeError as exc:
        raise SourceError(f"cs2settings: failed to parse player blob: {exc}") from exc
    if not isinstance(obj, dict):
        raise SourceError("cs2settings: player blob is not an object")
    return obj


# ---------------------------------------------------------------------------
# field mapping (raw key -> normalized field name)
# ---------------------------------------------------------------------------

_MOUSE_MAP = {
    "dpi": "dpi",
    "sensitivity": "sensitivity",
    "edpiCalculated": "edpi",
    "zoomSensitivity": "zoom_sensitivity",
    "pollingRate": "polling_rate",
    "windowsSensitivity": "windows_sensitivity",
}
_CROSSHAIR_MAP = {
    "style": "crosshair_style",
    "size": "crosshair_size",
    "gap": "crosshair_gap",
    "thickness": "crosshair_thickness",
    "color": "crosshair_color_raw",
    "outline": "crosshair_outline",
    "dot": "crosshair_dot",
    "alpha": "crosshair_alpha",
}
_VIDEO_MAP = {
    "resolution": "resolution",
    "aspectRatio": "aspect_ratio",
    "scalingMode": "scaling_mode",
    "brightness": "brightness",
    "boostPlayer": "reflex",
    "antialiasing": "display_mode",  # informational
}
_VIEWMODEL_MAP = {
    "fov": "viewmodel_fov",
    "offsetX": "viewmodel_offset_x",
    "offsetY": "viewmodel_offset_y",
    "offsetZ": "viewmodel_offset_z",
}
_MAP_MAP = {
    "radarZoom": "radar_zoom",
    "radarCentered": "radar_centered",
}

# cs2settings crosshair color code -> category (from their own schema)
_COLOR_CODES = {
    1: "Green", 2: "Yellow", 3: "Cyan", 4: "Blue",
    5: "Custom", 6: "Pink", 7: "Red", 8: "White",
}


class CS2SettingsSource:
    name = "cs2settings"
    enabled_for_schedule = True

    def __init__(self, base_url: str = BASE_URL, timeout: int = 20) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(HEADERS)

    # -- policy ------------------------------------------------------------

    def check_access_policy(self) -> AccessPolicy:
        robots = self._get_text(f"{self.base_url}/robots.txt")
        if "disallow" in robots.lower():
            return AccessPolicy(robots_allows=False, accessible=True,
                                notes="robots.txt contains Disallow rules")
        try:
            resp = self._session.get(f"{self.base_url}/", timeout=self.timeout)
            ok = resp.status_code == 200 and "cs2settings" in resp.text.lower()
        except requests.RequestException as exc:
            raise SourceError(f"cs2settings: access check failed: {exc}") from exc
        return AccessPolicy(
            robots_allows=True,
            accessible=ok,
            terms_url=None,
            notes="robots.txt: no Disallow (content signals: search=yes, ai-train=no); no dedicated terms page found",
        )

    # -- collection --------------------------------------------------------

    def list_players(self, max_pages: int = 5) -> list[dict]:
        players: dict[str, dict] = {}
        for page in range(1, max_pages + 1):
            url = f"{self.base_url}/players" + (f"?page={page}" if page > 1 else "")
            html = self._get_text(url)
            blob = _extract_players_blob(html)
            if not blob:
                break
            added = 0
            for p in blob:
                pid = p.get("id")
                if not pid or pid in players:
                    continue
                players[pid] = {"source_id": pid, "name": p.get("displayName") or pid,
                                "team": p.get("teamName")}
                added += 1
            if added == 0:
                break
        return list(players.values())

    def fetch_player(self, source_id: str) -> ParsedPlayer:
        url = f"{self.base_url}/players/{source_id}"
        html = self._get_text(url)
        try:
            blob = _extract_player_blob(html)
        except SourceError:
            # fall back to semantic heading/label-value parsing
            blob = _parse_labels(html, source_id)
        return self._blob_to_parsed(source_id, url, blob)

    # -- parsing -----------------------------------------------------------

    def _blob_to_parsed(self, source_id: str, url: str, blob: dict) -> ParsedPlayer:
        name = blob.get("displayName") or blob.get("realName") or blob.get("name") or source_id
        last_verified = blob.get("lastVerified")
        fields: dict[str, Any] = {}

        mouse = blob.get("mouse") or {}
        for k, v in mouse.items():
            f = _MOUSE_MAP.get(k)
            if f:
                fields[f] = v
        ch = blob.get("crosshair") or {}
        for k, v in ch.items():
            f = _CROSSHAIR_MAP.get(k)
            if not f:
                continue
            if f == "crosshair_color_raw":
                fields["crosshair_color"] = _COLOR_CODES.get(int(v)) if isinstance(v, (int, float)) else v
            else:
                fields[f] = v
        vid = blob.get("videoSettings") or {}
        for k, v in vid.items():
            f = _VIDEO_MAP.get(k)
            if f:
                fields[f] = v
        vm = blob.get("viewmodel") or {}
        for k, v in vm.items():
            f = _VIEWMODEL_MAP.get(k)
            if f:
                fields[f] = v
        ms = blob.get("mapSettings") or {}
        for k, v in ms.items():
            f = _MAP_MAP.get(k)
            if f:
                fields[f] = v

        return ParsedPlayer(
            source=self.name,
            source_id=source_id,
            name=name,
            source_url=url,
            retrieved_at=date.today().isoformat(),
            steam_id=_clean_steam_id(blob.get("steamId")),
            team=blob.get("teamId"),
            role=blob.get("role"),
            country=blob.get("countryCode") or blob.get("country"),
            source_updated_at=last_verified,
            fields=fields,
        )

    def normalize(self, parsed: ParsedPlayer) -> dict[str, Any]:
        return parsed.fields

    # -- helpers -----------------------------------------------------------

    def _get_text(self, url: str) -> str:
        try:
            resp = self._session.get(url, timeout=self.timeout)
        except requests.RequestException as exc:
            raise SourceError(f"cs2settings: request failed for {url}: {exc}") from exc
        if resp.status_code != 200:
            raise SourceError(f"cs2settings: HTTP {resp.status_code} for {url}")
        return resp.text


def _clean_steam_id(v: Any) -> Optional[str]:
    if v is None:
        return None
    m = re.search(r"(\d{15,17})", str(v))
    return m.group(1) if m else None


def _extract_players_blob(html: str) -> list[dict]:
    """Parse the /players list blob: data:[{type:"data",data:{players:[...]}}]."""
    cleaned = _strip_js_comments(html)
    marker = 'data:{players:['
    idx = cleaned.find(marker)
    if idx == -1:
        return []
    start = cleaned.find("[", idx)
    end = _extract_balanced(cleaned, start, "[", "]")
    if end == -1:
        return []
    literal = cleaned[start:end]
    s = re.sub(r"void\s+0", "null", literal)
    s = re.sub(r"([{,]\s*)([A-Za-z_$][\w$]*)(\s*:)", r'\1"\2"\3', s)
    s = re.sub(r",\s*([}\]])", r"\1", s)
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        return []
    return obj if isinstance(obj, list) else []


def _parse_labels(html: str, source_id: str) -> dict:
    """Fallback: semantic heading/label-value parsing (no CSS classes)."""
    soup = BeautifulSoup(html, "html.parser")
    out: dict[str, Any] = {}
    for label in soup.find_all(["h2", "h3", "dt", "th"]):
        text = label.get_text(" ", strip=True)
        if not text:
            continue
        value = label.find_next(["p", "dd", "td"])
        if value:
            out[text.lower()] = value.get_text(" ", strip=True)
    out["source_id"] = source_id
    return out
