"""Source adapter contract.

Every adapter MUST:
- use plain HTTP (requests/httpx) + HTML parsing only;
- never bypass anti-bot measures, fake cookies, rotate proxies, solve
  CAPTCHAs, or use browser automation;
- fail closed: on any access or parse failure it raises SourceError and the
  pipeline treats the source as unavailable (no silent fallback to another
  source for the same data role).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol


class SourceError(Exception):
    """Raised when a source cannot be accessed or parsed."""


class PolicyBlocked(SourceError):
    """Raised when robots.txt / terms block collection."""


@dataclass
class AccessPolicy:
    robots_allows: bool
    accessible: bool
    terms_url: Optional[str] = None
    notes: str = ""


@dataclass
class ParsedPlayer:
    """One player's parsed raw record from a source."""

    source: str
    source_id: str  # stable source-internal id (e.g. cs2settings slug)
    name: str
    source_url: str
    retrieved_at: str  # ISO date
    steam_id: Optional[str] = None
    team: Optional[str] = None
    role: Optional[str] = None
    country: Optional[str] = None
    source_updated_at: Optional[str] = None  # source's "last verified" date
    fields: dict[str, Any] = field(default_factory=dict)  # raw field name -> raw value


class SettingsSource(Protocol):
    name: str
    enabled_for_schedule: bool

    def check_access_policy(self) -> AccessPolicy:
        raise NotImplementedError

    def list_players(self) -> list[dict]:
        """List available players: [{"source_id": str, "name": str, ...}].

        Fails closed on error.
        """
        raise NotImplementedError

    def fetch_player(self, source_id: str) -> ParsedPlayer:
        """Fetch and parse one player. Fails closed on error."""
        raise NotImplementedError

    def normalize(self, parsed: ParsedPlayer) -> dict[str, Any]:
        """Map raw fields to normalized field names (see normalize.py)."""
        raise NotImplementedError
