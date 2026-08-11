"""Multi-source reconciliation.

Rules:
1. conflicting values are NEVER silently overwritten: every disagreement is
   recorded as a conflict (player_id, field, source_a, value_a, source_b, value_b);
2. the primary value is chosen by field-priority configuration
   (config/sources.yaml -> field_priority);
3. disabled sources are skipped automatically.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .models import NormalizedPlayerSettings, PlayerIdentity, SourceObservation


@dataclass
class ReconcileResult:
    players: dict[str, NormalizedPlayerSettings] = field(default_factory=dict)
    conflicts: list[dict] = field(default_factory=list)
    skipped_observations: int = 0


def _provenance_for(obs: SourceObservation) -> dict:
    return {
        "source": obs.source,
        "source_url": obs.source_url,
        "retrieved_at": obs.retrieved_at,
        "source_updated_at": obs.source_updated_at,
    }


def reconcile(
    observations: list[SourceObservation],
    field_priority: dict[str, list[str]],
    enabled_sources: set[str],
    identities: Optional[dict[str, "PlayerIdentity"]] = None,
) -> ReconcileResult:
    """Merge observations into per-player normalized settings.

    field_priority maps a field group ('crosshair', 'dpi', 'gear', ...) to an
    ordered list of sources. A field belongs to a group by the first group that
    names any of its raw names; if no group matches, any enabled source wins.

    identities (player_id -> PlayerIdentity) propagates canonical_name and
    team so settings records never degrade to player_id-only stubs.
    """
    identities = identities or {}
    # group -> set of normalized attributes
    group_attrs: dict[str, set[str]] = {}
    for group, attrs in _GROUP_ATTRS.items():
        group_attrs[group] = attrs

    # raw field name -> group (first match wins)
    from .normalize import _PARSERS

    raw_to_group: dict[str, str] = {}
    for raw in _PARSERS:
        for group, attrs in group_attrs.items():
            attr = _PARSERS[raw][0]
            if attr in attrs:
                raw_to_group[raw] = group
                break

    # per player: attribute -> list of observations (enabled sources only)
    by_player: dict[str, dict[str, list[SourceObservation]]] = {}
    for obs in observations:
        if obs.source not in enabled_sources:
            continue
        by_player.setdefault(obs.player_id, {}).setdefault(obs.field, []).append(obs)

    # COHORT PRESERVATION: the player universe is observation-driven ∪
    # identity-driven. A player with a stable identity from this collection
    # run (fetched + inclusion-allowed) stays a cohort member even with
    # ZERO parseable settings observations — settings availability must not
    # decide cohort membership.
    player_ids = set(by_player) | set(identities)

    result = ReconcileResult()
    for player_id in sorted(player_ids):
        identity = identities.get(player_id)
        settings = NormalizedPlayerSettings(
            player_id=player_id,
            canonical_name=identity.canonical_name if identity else player_id,
            team=identity.team if identity else None,
        )
        for attr, obs_list in (by_player.get(player_id) or {}).items():
            if not obs_list:
                continue
            # dedupe by (source): keep the most recent retrieval
            by_source: dict[str, SourceObservation] = {}
            for obs in obs_list:
                cur = by_source.get(obs.source)
                if cur is None or obs.retrieved_at >= cur.retrieved_at:
                    by_source[obs.source] = obs
            obs_list = list(by_source.values())

            if len(obs_list) == 1:
                chosen = obs_list[0]
            else:
                # multiple sources: record conflicts, then pick by priority
                chosen = _pick_primary(obs_list, field_priority, raw_to_group, result, player_id, attr)

            value = chosen.value
            if value is not None:
                setattr(settings, attr, value)
                settings.provenance[attr] = _provenance_for(chosen)
        result.players[player_id] = settings

    return result


def _pick_primary(
    obs_list: list[SourceObservation],
    field_priority: dict[str, list[str]],
    raw_to_group: dict[str, str],
    result: ReconcileResult,
    player_id: str,
    attr: str,
) -> SourceObservation:
    """Select the primary observation and record all disagreements."""
    # collect distinct values per source
    values: dict[str, Any] = {}
    for obs in obs_list:
        values[obs.source] = obs.value

    # conflicts: report every pair of sources whose values differ
    seen: set[tuple[str, ...]] = set()
    for i, a in enumerate(obs_list):
        for b in obs_list[i + 1 :]:
            key = tuple(sorted([a.source, b.source]))
            if key in seen or a.value == b.value:
                continue
            seen.add(key)
            result.conflicts.append(
                {
                    "player_id": player_id,
                    "field": attr,
                    "source_a": a.source,
                    "value_a": a.value,
                    "source_b": b.source,
                    "value_b": b.value,
                }
            )

    group = raw_to_group.get(attr)
    priority = field_priority.get(group, []) if group else []
    rank = {s: i for i, s in enumerate(priority)}
    best = min(obs_list, key=lambda o: (rank.get(o.source, len(rank)), o.retrieved_at))
    return best


_GROUP_ATTRS: dict[str, set[str]] = {
    "crosshair": {
        "crosshair_style", "crosshair_size", "crosshair_gap", "crosshair_thickness",
        "crosshair_color", "crosshair_color_code", "crosshair_color_r",
        "crosshair_color_g", "crosshair_color_b",
        "crosshair_outline", "crosshair_dot", "crosshair_alpha",
    },
    "dpi": {"dpi", "sensitivity", "edpi", "zoom_sensitivity", "polling_rate"},
    "gear": {"resolution", "aspect_ratio", "scaling_mode", "refresh_rate", "max_fps"},
    "video": {"brightness", "vsync", "reflex"},
    "viewmodel": {"viewmodel_fov", "viewmodel_offset_x", "viewmodel_offset_y", "viewmodel_offset_z"},
    "radar": {"radar_zoom", "radar_centered", "radar_rotating"},
}
