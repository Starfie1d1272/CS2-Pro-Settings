"""Versioned crosshair semantics shared by metrics and adapters.

legacy-v3/v4 are transitional pixel formats, despite their names. Never
convert geometry or infer a reference height from the player's resolution.
"""
from .models import CUSTOM_COLOR_CODE

PIXEL_FORMATS = {"cs2-v1", "legacy-v3", "legacy-v4"}
LEGACY_FORMATS = {"legacy", "legacy-v1", "csgo"}


def format_of(player):
    return player.crosshair_format or "legacy"


def active_rgb(player):
    fmt = format_of(player)
    return fmt in PIXEL_FORMATS or (
        fmt in LEGACY_FORMATS and player.crosshair_color_code == CUSTOM_COLOR_CODE)


def outline_mode(player):
    fmt = format_of(player)
    if fmt not in PIXEL_FORMATS | LEGACY_FORMATS:
        return None
    mode = player.crosshair_outline_mode
    if mode in (0, 1, 2) and not isinstance(mode, bool):
        return mode
    if fmt in LEGACY_FORMATS or fmt == "legacy-v3":
        if player.crosshair_outline is not None:
            return int(player.crosshair_outline)
    return None


def geometry_context(player):
    fmt = format_of(player)
    if fmt in LEGACY_FORMATS:
        return "legacy-units"
    if fmt in PIXEL_FORMATS:
        height = player.crosshair_screen_height
        return f"{fmt}:px@{height}" if height and height > 0 else f"{fmt}:px@unknown"
    return f"{fmt}:unknown-units"
