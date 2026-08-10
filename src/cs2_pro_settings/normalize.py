"""Field normalization.

All parsing rules live here, not inside source adapters:
- numeric parsing (commas, percent, units);
- Hz extraction;
- resolutions / aspect ratios;
- Yes/No/Enabled/Disabled booleans;
- crosshair color categories;
- missing values -> None.

Every normalized field is attached to a SourceObservation so provenance is
preserved end to end.
"""
from __future__ import annotations

import re
from typing import Any, Optional

# ---------------------------------------------------------------------------
# scalar parsers
# ---------------------------------------------------------------------------

_KNOWN_COLORS = ["Custom", "Cyan", "Green", "Yellow", "Blue", "Red", "White", "Pink", "Purple", "Orange"]


def to_float(v: Any) -> Optional[float]:
    """'1,200' -> 1200.0; '93%' -> 93.0; '400dpi' -> 400.0; junk -> None."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().lower()
    s = s.replace(",", "").replace("%", "").replace("hz", "").replace("dpi", "")
    s = re.sub(r"[^0-9.\-]", "", s)
    if not s or s in {".", "-"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def to_int(v: Any) -> Optional[int]:
    f = to_float(v)
    return int(f) if f is not None and f.is_integer() else (int(f) if f is not None else None)


def to_hz(v: Any) -> Optional[int]:
    """Extract the leading integer from strings like '1000Hz' / '1,000 Hz'."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    m = re.search(r"(\d+)", str(v).replace(",", ""))
    return int(m.group(1)) if m else None


def parse_resolution(v: Any) -> Optional[tuple[int, int]]:
    """'1280x960' -> (1280, 960); anything else -> None."""
    if v is None:
        return None
    m = re.search(r"(\d{3,5})\s*[xX×]\s*(\d{3,5})", str(v))
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def to_bool(v: Any) -> Optional[bool]:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in {"yes", "enabled", "true", "on", "1", "enable"}:
        return True
    if s in {"no", "disabled", "false", "off", "0", "disable"}:
        return False
    return None


def clean_string(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def color_category(v: Any) -> Optional[str]:
    """Map a raw crosshair color label to a stable category.

    'Custom (255,255,255)' -> 'Custom'; 'cyan' -> 'Cyan'; unknown -> None.
    """
    if v is None:
        return None
    s = str(v).strip()
    for c in _KNOWN_COLORS:
        if s.lower().startswith(c.lower()):
            return c
    if s.lower().startswith("custom") or "rgb" in s.lower():
        return "Custom"
    return None


# ---------------------------------------------------------------------------
# field registry: raw field name -> (settings attribute, parser)
# ---------------------------------------------------------------------------

_PARSERS: dict[str, tuple[str, Any]] = {
    # mouse
    "dpi": ("dpi", to_float),
    "sensitivity": ("sensitivity", to_float),
    "edpi": ("edpi", to_float),
    "edpi_calculated": ("edpi", to_float),
    "zoom_sensitivity": ("zoom_sensitivity", to_float),
    "polling_rate": ("polling_rate", to_hz),
    "windows_sensitivity": ("windows_sensitivity", to_int),  # informational
    # display
    "resolution": ("resolution", clean_string),
    "aspect_ratio": ("aspect_ratio", clean_string),
    "scaling_mode": ("scaling_mode", clean_string),
    "refresh_rate": ("refresh_rate", to_hz),
    "brightness": ("brightness", to_float),
    "vsync": ("vsync", clean_string),
    "reflex": ("reflex", clean_string),
    "boost_player": ("boost_player", clean_string),  # informational
    "max_fps": ("max_fps", to_int),
    "display_mode": ("display_mode", clean_string),  # informational
    # crosshair
    "crosshair_style": ("crosshair_style", clean_string),
    "style": ("crosshair_style", clean_string),
    "crosshair_size": ("crosshair_size", to_float),
    "size": ("crosshair_size", to_float),
    "crosshair_gap": ("crosshair_gap", to_float),
    "gap": ("crosshair_gap", to_float),
    "crosshair_thickness": ("crosshair_thickness", to_float),
    "thickness": ("crosshair_thickness", to_float),
    "crosshair_color": ("crosshair_color", color_category),
    "color": ("crosshair_color", color_category),
    "crosshair_outline": ("crosshair_outline", to_bool),
    "outline": ("crosshair_outline", to_bool),
    "crosshair_dot": ("crosshair_dot", to_bool),
    "dot": ("crosshair_dot", to_bool),
    "crosshair_alpha": ("crosshair_alpha", to_int),
    "alpha": ("crosshair_alpha", to_int),
    # viewmodel
    "viewmodel_fov": ("viewmodel_fov", to_float),
    "fov": ("viewmodel_fov", to_float),
    "viewmodel_offset_x": ("viewmodel_offset_x", to_float),
    "offset_x": ("viewmodel_offset_x", to_float),
    "viewmodel_offset_y": ("viewmodel_offset_y", to_float),
    "offset_y": ("viewmodel_offset_y", to_float),
    "viewmodel_offset_z": ("viewmodel_offset_z", to_float),
    "offset_z": ("viewmodel_offset_z", to_float),
    # radar / HUD
    "radar_zoom": ("radar_zoom", to_float),
    "radar_centered": ("radar_centered", to_bool),
    "radar_rotating": ("radar_rotating", to_bool),
}

# informational fields kept in observations but not used in metrics
INFORMATIONAL = {"windows_sensitivity", "boost_player", "display_mode"}


def normalize_field(raw_name: str, value: Any) -> tuple[Optional[str], Any]:
    """Normalize one raw field.

    Returns (settings_attribute, normalized_value); unknown fields -> (None, None).
    """
    entry = _PARSERS.get(raw_name.lower())
    if not entry:
        return None, None
    attr, parser = entry
    try:
        return attr, parser(value)
    except (TypeError, ValueError):
        return attr, None
