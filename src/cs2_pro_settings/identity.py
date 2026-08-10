"""Player identity resolution.

Canonical player_id rules:
    - steam:<steamid>  if a SteamID is available (preferred);
    - source:<source>:<stable-source-id> otherwise.

A bare nickname is NEVER used as a permanent unique ID.
"""
from __future__ import annotations

from typing import Optional

from .models import PlayerIdentity


def canonical_player_id(steam_id: Optional[str], source: str, source_id: str) -> str:
    if steam_id:
        return f"steam:{steam_id}"
    return f"source:{source}:{source_id}"


class IdentityIndex:
    """Resolve stable identities across observations and sources.

    Merging rule: same SteamID -> same player, regardless of nickname or team
    spelling changes.  If no SteamID is known, a (source, source_id) pair is the
    stable key; a source_id collision with conflicting SteamIDs is reported as
    an identity problem instead of being silently merged.
    """

    def __init__(self) -> None:
        self._by_steam: dict[str, str] = {}  # steam_id -> player_id
        self._by_source: dict[tuple[str, str], str] = {}  # (source, source_id) -> player_id
        self._players: dict[str, PlayerIdentity] = {}
        self.identity_problems: list[dict] = []

    def register(
        self,
        *,
        source: str,
        source_id: str,
        name: str,
        team: Optional[str] = None,
        steam_id: Optional[str] = None,
        country: Optional[str] = None,
        role: Optional[str] = None,
    ) -> PlayerIdentity:
        """Register or merge a player observation; returns the canonical identity."""
        source_key = (source, source_id)

        # 1. Prefer SteamID as the canonical key.
        if steam_id:
            existing = self._by_steam.get(steam_id)
            if existing:
                pid = self._players[existing]
                # same steam id claimed by a different source id -> link them
                pid.source_ids.setdefault(source, source_id)
                if source_key in self._by_source and self._by_source[source_key] != existing:
                    # another player was already keyed to this source id without steam
                    self.identity_problems.append(
                        {
                            "type": "steam_collision",
                            "source": source,
                            "source_id": source_id,
                            "steam_id": steam_id,
                            "existing_player_id": existing,
                            "previous_player_id": self._by_source[source_key],
                        }
                    )
                return pid

        # 2. Known (source, source_id)?
        existing = self._by_source.get(source_key)
        if existing:
            pid = self._players[existing]
            if steam_id and not pid.steam_id:
                pid.steam_id = steam_id
                self._by_steam[steam_id] = existing
            return pid

        # 3. New identity.
        pid = canonical_player_id(steam_id, source, source_id)
        self._players[pid] = PlayerIdentity(
            player_id=pid,
            canonical_name=name,
            team=team,
            steam_id=steam_id,
            country=country,
            role=role,
            source_ids={source: source_id},
        )
        if steam_id:
            self._by_steam[steam_id] = pid
        self._by_source[source_key] = pid
        return self._players[pid]

    def get(self, player_id: str) -> Optional[PlayerIdentity]:
        return self._players.get(player_id)

    def all(self) -> list[PlayerIdentity]:
        return sorted(self._players.values(), key=lambda p: p.player_id)

    def player_count(self) -> int:
        return len(self._players)
