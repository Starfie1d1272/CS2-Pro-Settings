"""Core data models for the CS2 settings pipeline.

Design rules:
- missing is legal: every optional field defaults to None;
- a canonical player_id must never be a bare nickname;
- provenance is attached per field, not per record.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PlayerIdentity:
    """Stable identity of a tracked professional player.

    player_id is canonical and persistent:
      - steam:<steamid> when a SteamID is available;
      - source:<source>:<stable-source-id> otherwise.
    """

    player_id: str
    canonical_name: str
    team: Optional[str] = None
    steam_id: Optional[str] = None
    country: Optional[str] = None
    role: Optional[str] = None
    source_ids: dict[str, str] = field(default_factory=dict)
    # source -> stable source-internal id (e.g. cs2settings slug)


@dataclass
class SourceObservation:
    """A single field value observed from one source."""

    player_id: str
    field: str
    value: Any
    source: str
    source_url: str
    retrieved_at: str  # ISO-8601 date of retrieval
    source_updated_at: Optional[str] = None  # source's own "last verified" date
    confidence: float = 1.0
    raw_label: Optional[str] = None


@dataclass
class NormalizedPlayerSettings:
    """Normalized settings for one player.

    Provenance maps field name -> dict with:
        source, source_url, retrieved_at, source_updated_at (optional)
    """

    player_id: str
    canonical_name: str
    team: Optional[str] = None

    # mouse
    dpi: Optional[float] = None
    sensitivity: Optional[float] = None
    edpi: Optional[float] = None
    zoom_sensitivity: Optional[float] = None
    polling_rate: Optional[int] = None

    # display
    resolution: Optional[str] = None
    aspect_ratio: Optional[str] = None
    scaling_mode: Optional[str] = None
    refresh_rate: Optional[int] = None
    brightness: Optional[float] = None
    vsync: Optional[str] = None  # "Enabled" | "Disabled"
    reflex: Optional[str] = None
    max_fps: Optional[int] = None

    # crosshair
    crosshair_style: Optional[str] = None
    crosshair_size: Optional[float] = None
    crosshair_gap: Optional[float] = None
    crosshair_thickness: Optional[float] = None
    crosshair_color: Optional[str] = None
    crosshair_outline: Optional[bool] = None
    crosshair_dot: Optional[bool] = None
    crosshair_alpha: Optional[int] = None

    # viewmodel
    viewmodel_fov: Optional[float] = None
    viewmodel_offset_x: Optional[float] = None
    viewmodel_offset_y: Optional[float] = None
    viewmodel_offset_z: Optional[float] = None

    # radar / HUD
    radar_zoom: Optional[float] = None
    radar_centered: Optional[bool] = None
    radar_rotating: Optional[bool] = None

    provenance: dict[str, dict] = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "provenance"}
        d["provenance"] = self.provenance
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "NormalizedPlayerSettings":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # noqa: B009
        kwargs = {k: v for k, v in d.items() if k in known}
        return cls(**kwargs)


@dataclass
class SourceHealth:
    """Result of a source policy/access check."""

    source: str
    accessible: bool
    robots_allows: bool
    message: str
    checked_at: str
    enabled: bool
