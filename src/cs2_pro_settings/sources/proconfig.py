"""Pro Config adapter — secondary editorial cross-check (DISABLED).

Audit result (docs/source-audit/proconfig.md): the domain proconfig.gg is not
registered (whois NOT FOUND); DNS resolves to a local sinkhole
(198.18.0.11 — fake-ip). prosettings.gg returns HTTP 466 (Cloudflare
challenge). Technical access is therefore NOT available.

The adapter exists so the pipeline shape is complete, but it is disabled in
config/sources.yaml and always fails closed.
"""
from __future__ import annotations

from typing import Any

from .base import AccessPolicy, ParsedPlayer, SourceError

BASE_URL = "https://proconfig.gg"


class ProConfigSource:
    name = "proconfig"
    enabled_for_schedule = False

    def check_access_policy(self) -> AccessPolicy:
        return AccessPolicy(
            robots_allows=False,
            accessible=False,
            terms_url=None,
            notes="domain proconfig.gg not registered (whois NOT FOUND); "
                  "no technical access available; adapter disabled",
        )

    def list_players(self) -> list[dict]:
        raise SourceError("proconfig: source disabled (domain not registered)")

    def fetch_player(self, source_id: str) -> ParsedPlayer:
        raise SourceError("proconfig: source disabled (domain not registered)")

    def normalize(self, parsed: ParsedPlayer) -> dict[str, Any]:
        raise SourceError("proconfig: source disabled (domain not registered)")
