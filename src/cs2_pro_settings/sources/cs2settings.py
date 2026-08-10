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


def _iter_script_bodies(html: str):
    """Yield non-empty <script> bodies via BeautifulSoup (HTML-level only)."""
    soup = BeautifulSoup(html, "html.parser")
    for s in soup.find_all("script"):
        body = s.string
        if body and body.strip():
            yield body


def _scan_balanced(text: str, start: int, open_ch: str, close_ch: str) -> int:
    """String- and comment-aware balanced bracket scan.

    States: code / string / line-comment / block-comment.
    - Only outside strings: `//` is a line comment, `/* */` a block comment.
    - Only outside comments: quotes toggle string state (", ', `).
    - Backslash escapes are honored character-by-character inside strings:
      `\` escapes the NEXT character only (so `\\"` keeps the string open
      through a backslash-escaped quote, and `\\` + `"` correctly closes).
    Returns the index AFTER the matching close bracket, or -1.
    """
    depth = 0
    i, n = start, len(text)
    state = "code"
    quote = ""
    escaped = False
    while i < n:
        ch = text[i]
        if state == "string":
            if ch == "\\" and not escaped:
                escaped = True
                i += 1
                continue
            if ch == quote and not escaped:
                state = "code"
            escaped = False
            i += 1
            continue
        if state == "line":
            if ch == "\n":
                state = "code"
            i += 1
            continue
        if state == "block":
            if ch == "*" and i + 1 < n and text[i + 1] == "/":
                state = "code"
                i += 2
                continue
            i += 1
            continue
        # code state
        if ch in ('"', "'", "`"):
            state = "string"
            quote = ch
            i += 1
            continue
        if ch == "/" and i + 1 < n:
            if text[i + 1] == "/":
                state = "line"
                i += 2
                continue
            if text[i + 1] == "*":
                state = "block"
                i += 2
                continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


_PLAYER_MARKER = "data:{player:{"
_PLAYER_SENTINELS = ("steamId", "lastVerified", "crosshairSource", "skinsAsOf",
                     "mouse", "videoSettings", "viewmodel", "mapSettings")
_ROSTER_ROLES = ("igl", "rifler", "awper", "entry fragger", "sniper", "lurker",
                 "captain", "coach", "support")


def _extract_player_blob(html: str) -> dict:
    """Extract the embedded `data:{player:{...}}` object (two-level strategy).

    Level 1: parse HTML with BeautifulSoup, consider each <script> body only.
    Level 2: within a single script body, locate a high-specificity marker
    (`data:{player:{`), or fall back to scanning backwards from `steamId:`
    sentinel candidates, then run a string/comment-aware balanced-brace scan.

    Returns the player dict; raises SourceError if not found/parseable.
    """
    for body in _iter_script_bodies(html):
        obj = _try_parse_player_body(body)
        if obj is not None:
            return obj
    raise SourceError("cs2settings: player data blob not found")


def _try_parse_player_body(body: str):
    """Try to parse a player object from one script body; None if not present."""
    # preferred: the SvelteKit data marker
    idx = body.find(_PLAYER_MARKER)
    if idx != -1:
        start = idx + len(_PLAYER_MARKER) - 1  # the '{' after 'player:'
        obj = _try_balanced(body, start, _PLAYER_MARKER)
        if obj is not None:
            return obj
    # fallback: nearest '{' candidates before the steamId sentinel
    sidx = body.find("steamId:")
    if sidx != -1:
        lo = max(0, sidx - 4000)
        pos = body.rfind("{", lo, sidx)
        tried = 0
        while pos != -1 and tried < 6:
            obj = _try_balanced(body, pos, f"sentinel@{pos}")
            if obj is not None:
                return obj
            tried += 1
            pos = body.rfind("{", lo, pos - 1)
    return None


def _try_balanced(body: str, start: int, tag: str):
    """Balanced scan + parse + validation; None on any failure."""
    end = _scan_balanced(body, start, "{", "}")
    if end == -1:
        return None
    literal = body[start:end]
    try:
        obj = _js_literal_to_json(literal)
    except SourceError:
        return None
    if isinstance(obj, dict) and "mouse" in obj and ("steamId" in obj or "videoSettings" in obj):
        return obj
    return None


_KEY_RE = re.compile(r"([{,][ \t\n\r]*|^[ \t\n\r]*)([A-Za-z_$][\w$]*)[ \t\n\r]*:")


def _js_literal_to_json(literal: str) -> dict:
    """Convert a JS object literal to a Python dict (tolerant, string-aware).

    The blob is SvelteKit JSON-serialized data, so strings use double quotes
    only. Inside strings, backslash escapes are normalized: `\\'` -> `'`,
    everything else is kept verbatim (so `\\"`, `\\\\`, `\\n` stay valid JSON).
    """
    s = literal
    s = re.sub(r"void\s+0", "null", s)
    s = re.sub(r"\bundefined\b", "null", s)
    s = re.sub(r"NaN", "null", s)
    out: list[str] = []
    i, n = 0, len(s)
    in_str = False
    while i < n:
        ch = s[i]
        if in_str:
            if ch == "\\":
                # escape: normalize \' -> ' (valid JS, invalid JSON)
                if i + 1 < n and s[i + 1] == "'":
                    out.append("'")
                else:
                    out.append(ch)
                    if i + 1 < n:
                        out.append(s[i + 1])
                i += 2
                continue
            if ch == '"':
                in_str = False
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue
        # trailing comma before } or ] -> drop it
        if ch == ",":
            j = i + 1
            while j < n and s[j] in " \t\n\r":
                j += 1
            if j < n and s[j] in "}]":
                i = j
                continue
        # unquoted key: ( { , whitespace ) ident ( whitespace ) :
        if ch in "{," or ch in " \t\n\r":
            m = _KEY_RE.match(s, i)
            if m:
                out.append(m.group(1))
                out.append('"' + m.group(2) + '":')
                i = m.end()
                continue
        # JS shorthand decimal: .7 -> 0.7 (invalid JSON as-is)
        if ch == "." and i + 1 < n and s[i + 1].isdigit() and (i == 0 or s[i - 1] not in "0123456789_.\w"):
            out.append("0")
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

    def list_team_roster(self, team_slug: str) -> list[dict]:
        """Parse the current active roster of a team from its team page.

        Semantic anchor: roster links contain a role marker (IGL / Rifler /
        AWPer / Entry Fragger / Sniper / Lurker / Captain / Coach) as text;
        CSS class names are NOT used as parser anchors. Footer/nav links to
        players of other teams (no role marker) are excluded.
        """
        url = f"{self.base_url}/teams/{team_slug}"
        html = self._get_text(url)
        soup = BeautifulSoup(html, "html.parser")
        roster: list[dict] = []
        seen: set[str] = set()
        for a in soup.find_all("a", href=True):
            href = a["href"] or ""
            if "/players/" not in href:
                continue
            pid = href.rstrip("/").split("/")[-1]
            if not pid or pid in seen:
                continue
            text = a.get_text(" ", strip=True)
            low = text.lower()
            if not any(low.endswith(r) for r in _ROSTER_ROLES):
                continue
            role = next((r for r in _ROSTER_ROLES if low.endswith(r)), None)
            name = text[: -len(role)].strip() if role else pid
            seen.add(pid)
            roster.append({"source_id": pid, "name": name or pid})
        return roster

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
    """Parse the /players list blob within a single script body.

    Marker: data:[{type:"data",data:{players:[...]}}] — balanced-bracket scan
    on the '[' after the marker, using the string/comment-aware scanner.
    """
    for body in _iter_script_bodies(html):
        marker = "data:{players:["
        idx = body.find(marker)
        if idx == -1:
            continue
        start = body.find("[", idx)
        if start == -1:
            continue
        end = _scan_balanced(body, start, "[", "]")
        if end == -1:
            continue
        literal = body[start:end]
        try:
            obj = _js_literal_to_json('{"__list":' + literal + "}")
            lst = obj.get("__list")
        except SourceError:
            continue
        if isinstance(lst, list):
            return lst
    return []


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
