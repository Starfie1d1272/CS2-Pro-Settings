"""Deterministic production figures with a restrained editorial style.

The report uses five information-dense figures rather than one chart per
field: mouse, display, crosshair geometry, crosshair color, and radar.
All bars show shares of the field's own valid_n.  Empty blocks do not create
figures, and no chart implies semantics beyond the source-provided values.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402

PAPER = "#f7f6f3"
INK = "#17212b"
MUTED = "#64707d"
GRID = "#d9dde2"
ACCENT = "#2864a8"
ACCENT_2 = "#5f8f86"
SOFT = "#aeb8c2"
HAIRLINE = "#c9ced4"

_FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
DISPLAY_BOLD = FontProperties(fname=_FONT_DIR / "STIXGeneralBol.ttf")
BODY = FontProperties(fname=_FONT_DIR / "DejaVuSans.ttf")
BODY_BOLD = FontProperties(fname=_FONT_DIR / "DejaVuSans-Bold.ttf")

PRODUCTION_FILES = {
    "mouse.png", "display.png", "crosshair_geometry.png",
    "crosshair_color.png", "radar.png",
}
LEGACY_FILES = {
    "edpi.png", "dpi.png", "polling_rate.png", "aspect_ratio.png",
    "resolution.png", "refresh_rate.png", "crosshair_custom_rgb.png",
    "fov.png",
}

_EDPI_ORDER = ["0-400", "400-600", "600-800", "800-1000",
               "1000-1200", "1200-1600", "1600+"]
_POLLING_ORDER = ["1000", "2000", "4000", "8000"]
_EDPI_LABELS = {
    "0-400": "0–<400",
    "400-600": "400–<600",
    "600-800": "600–<800",
    "800-1000": "800–<1000",
    "1000-1200": "1000–<1200",
    "1200-1600": "1200–<1600",
    "1600+": "1600+",
}
_PRESET_COLORS = {
    "Red": "#d64b45",
    "Green": "#23b14d",
    "Yellow": "#d9bd24",
    "Blue": "#3678c8",
    "Cyan": "#18b8bf",
}


def _theme() -> None:
    plt.rcParams.update({
        "figure.facecolor": PAPER,
        "axes.facecolor": PAPER,
        "savefig.facecolor": PAPER,
        "axes.edgecolor": GRID,
        "axes.labelcolor": MUTED,
        "text.color": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "font.family": BODY.get_name(),
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 8.5,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
    })


def _numeric_key(value: Any) -> tuple[int, float, str]:
    try:
        return (0, float(value), str(value))
    except (TypeError, ValueError):
        return (1, 0.0, str(value))


def _ordered(cats: dict, order: list[str] | None = None,
             top_n: int | None = None,
             include_zero: bool = False) -> list[tuple[str, int]]:
    items = [(str(k), int(v)) for k, v in cats.items()
             if include_zero or v]
    if top_n is not None and len(items) > top_n:
        items = sorted(items, key=lambda item: (-item[1], item[0]))[:top_n]
    if order:
        pos = {key: i for i, key in enumerate(order)}
        return sorted(items, key=lambda item: (pos.get(item[0], len(pos)),
                                                _numeric_key(item[0])))
    return sorted(items, key=lambda item: _numeric_key(item[0]))


def _ranked(cats: dict, top_n: int = 8) -> list[tuple[str, int]]:
    return sorted(((str(k), int(v)) for k, v in cats.items() if v),
                  key=lambda item: (-item[1], item[0]))[:top_n]


def _style_axis(ax) -> None:
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="y", color=GRID, linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)


def _share_bars(ax, items: list[tuple[str, int]], valid_n: int, title: str,
                horizontal: bool = False, colors: list[str] | None = None) -> None:
    if not items or valid_n <= 0:
        ax.set_visible(False)
        return
    labels = [key for key, _ in items]
    shares = [count / valid_n * 100 for _, count in items]
    bar_colors = colors or [ACCENT] * len(items)
    if horizontal:
        y = list(range(len(items)))
        bars = ax.barh(y, shares, color=bar_colors, edgecolor=GRID, linewidth=0.8)
        ax.set_yticks(y, labels)
        ax.invert_yaxis()
        ax.set_xlabel("Share of valid observations (%)")
        for bar, share, (_label, count) in zip(bars, shares, items):
            ax.text(share + 0.7, bar.get_y() + bar.get_height() / 2,
                    f"{share:.1f}%  {count}/{valid_n}", va="center", fontsize=8,
                    color=INK)
        ax.grid(axis="x", color=GRID, linewidth=0.7, alpha=0.8)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.set_xlim(0, max(shares) * 1.25 if shares else 1)
    else:
        x = list(range(len(items)))
        bars = ax.bar(x, shares, color=bar_colors, edgecolor=PAPER, linewidth=0.6)
        ax.set_xticks(x, labels, rotation=30, ha="right")
        ax.set_ylabel("Share (%)")
        for bar, share in zip(bars, shares):
            ax.text(bar.get_x() + bar.get_width() / 2, share + 0.8,
                    f"{share:.1f}%", ha="center", va="bottom", fontsize=7.5,
                    color=INK)
        _style_axis(ax)
    ax.set_title(f"{title}  ·  n={valid_n}", loc="left", pad=8,
                 fontproperties=BODY_BOLD, fontsize=10)
    if not horizontal:
        ax.set_ylim(0, max(5.0, max(shares) * 1.18) if shares else 1)


def _finish(fig, path: Path) -> None:
    fig.subplots_adjust(left=0.09, right=0.96, bottom=0.11, top=0.88,
                        wspace=0.52, hspace=0.44)
    fig.savefig(path, dpi=150, metadata={"Software": "cs2-pro-settings"})
    plt.close(fig)


def _figure_title(fig, title: str, subtitle: str) -> None:
    fig.suptitle(title, x=0.055, y=0.985, ha="left", fontsize=18,
                 fontproperties=DISPLAY_BOLD, color=INK)
    fig.text(0.055, 0.94, subtitle, ha="left", va="top", fontsize=8.5,
             fontproperties=BODY, color=MUTED)


def _render_mouse(agg: dict, path: Path) -> bool:
    edpi = agg.get("edpi") or {}
    dpi = agg.get("dpi") or {}
    polling = agg.get("mouse_polling") or {}
    zoom = agg.get("zoom_sensitivity") or {}
    if not any((edpi.get("count"), dpi.get("valid_n"), polling.get("valid_n"),
                zoom.get("valid_n"))):
        return False
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    _figure_title(fig, "Mouse settings", "Shares use each field's own valid denominator")
    edpi_items = _ordered(edpi.get("distribution") or {}, _EDPI_ORDER,
                          include_zero=True)
    edpi_items = [(_EDPI_LABELS.get(label, label), count)
                  for label, count in edpi_items]
    _share_bars(axes[0, 0], edpi_items,
                int(edpi.get("count") or 0), "eDPI bins")
    _share_bars(axes[0, 1], _ordered(dpi.get("categories") or {}, top_n=8),
                int(dpi.get("valid_n") or 0), "DPI")
    _share_bars(axes[1, 0], _ordered(polling.get("categories") or {}, _POLLING_ORDER),
                int(polling.get("valid_n") or 0), "Polling rate (Hz)")
    _share_bars(axes[1, 1], _ordered(zoom.get("categories") or {}, top_n=10),
                int(zoom.get("valid_n") or 0), "Zoom sensitivity")
    _finish(fig, path)
    return True


def _render_display(agg: dict, path: Path) -> bool:
    resolution = agg.get("resolution") or {}
    aspect = agg.get("aspect_ratio") or {}
    scaling = agg.get("scaling_mode") or {}
    boost = agg.get("boost_player") or {}
    if not any((resolution.get("valid_n"), aspect.get("valid_n"),
                scaling.get("valid_n"), boost.get("valid_n"))):
        return False
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    _figure_title(fig, "Display settings", "Resolution is ranked horizontally; all shares use field-level valid_n")
    _share_bars(axes[0, 0], _ranked(resolution.get("categories") or {}, 8),
                int(resolution.get("valid_n") or 0), "Resolution", horizontal=True)
    _share_bars(axes[0, 1], _ranked(aspect.get("categories") or {}, 6),
                int(aspect.get("valid_n") or 0), "Aspect ratio")
    axes[0, 1].set_ylabel("")
    _share_bars(axes[1, 0], _ranked(scaling.get("categories") or {}, 6),
                int(scaling.get("valid_n") or 0), "Scaling mode")
    boost_n = int(boost.get("valid_n") or 0)
    boost_items = [("Enabled", int(boost.get("enabled_count") or 0)),
                   ("Disabled", int(boost.get("disabled_count") or 0))]
    _share_bars(axes[1, 1], boost_items, boost_n, "Boost Player Contrast",
                colors=[ACCENT_2, SOFT])
    axes[1, 1].set_ylabel("")
    if boost_n:
        axes[1, 1].text(0.99, 0.98,
                        f"Missing / unknown: {int(boost.get('missing_n') or 0)}",
                        transform=axes[1, 1].transAxes, ha="right", va="top",
                        fontsize=8, color=MUTED)
    _finish(fig, path)
    return True


def _format_number(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return str(int(number)) if number.is_integer() else f"{number:g}"


def _dominant(block: dict) -> tuple[str, int, int] | None:
    valid_n = int(block.get("valid_n") or 0)
    items = _ranked(block.get("categories") or {}, 1)
    if not items or not valid_n:
        return None
    return items[0][0], items[0][1], valid_n


def _render_joint_geometry(ax, joint: dict) -> bool:
    combinations = joint.get("combinations") or []
    valid_n = int(joint.get("valid_n") or 0)
    if not combinations or not valid_n:
        ax.set_visible(False)
        return False

    gaps = sorted({float(row["gap"]) for row in combinations})
    sizes = sorted({float(row["size"]) for row in combinations})
    gap_pos = {value: index for index, value in enumerate(gaps)}
    size_pos = {value: index for index, value in enumerate(sizes)}
    xs = [gap_pos[float(row["gap"])] for row in combinations]
    ys = [size_pos[float(row["size"])] for row in combinations]
    counts = [int(row["count"]) for row in combinations]
    marker_sizes = [28 + count / valid_n * 5200 for count in counts]

    ax.scatter(xs, ys, s=marker_sizes, color=ACCENT, alpha=0.9,
               edgecolor=PAPER, linewidth=1.0, zorder=3)
    for x, y, count in zip(xs, ys, counts):
        if count >= 2:
            ax.text(x, y, str(count), ha="center", va="center", fontsize=6.5,
                    color="white", fontproperties=BODY_BOLD, zorder=4)

    ax.set_xticks(range(len(gaps)), [_format_number(value) for value in gaps],
                  rotation=55, ha="right")
    ax.set_yticks(range(len(sizes)), [_format_number(value) for value in sizes])
    ax.set_xlabel("Gap — exact source categories in numeric order")
    ax.set_ylabel("Size — exact source categories in numeric order")
    ax.set_title(f"Gap × size concentration  ·  n={valid_n}", loc="left", pad=9,
                 fontproperties=BODY_BOLD, fontsize=10.5)
    ax.grid(axis="both", color=GRID, linewidth=0.55, alpha=0.72)
    ax.set_axisbelow(True)
    ax.spines[:].set_visible(False)
    ax.set_xlim(-0.8, len(gaps) - 0.2)
    ax.set_ylim(-0.7, len(sizes) - 0.3)

    return True


def _geometry_summary(ax, geometry: dict) -> None:
    rows: list[tuple[str, str, int, int]] = []
    for key, label in (("style", "Most common style"),
                       ("alpha", "Most common alpha")):
        result = _dominant(geometry.get(key) or {})
        if result:
            value, count, valid_n = result
            rows.append((label, value, count, valid_n))
    for key, label in (("dot", "Dot off"), ("outline", "Outline off")):
        block = geometry.get(key) or {}
        valid_n = int(block.get("valid_n") or 0)
        if valid_n:
            rows.append((label, "", int(block.get("disabled_count") or 0),
                         valid_n))
    if not rows:
        ax.set_visible(False)
        return

    ax.set_axis_off()
    ax.set_title("Other geometry signals", loc="left", pad=9,
                 fontproperties=BODY_BOLD, fontsize=10)
    ys = [0.80, 0.59, 0.38, 0.17]
    for y, (label, value, count, valid_n) in zip(ys, rows):
        share = count / valid_n * 100
        value_label = f"  {value}" if value else ""
        ax.text(0.0, y + 0.07, f"{label}{value_label}", transform=ax.transAxes,
                fontsize=8, color=MUTED, fontproperties=BODY)
        ax.text(0.0, y, f"{share:.1f}%", transform=ax.transAxes, va="top",
                fontsize=13, color=INK, fontproperties=DISPLAY_BOLD)
        ax.text(0.98, y, f"{count}/{valid_n}", transform=ax.transAxes,
                ha="right", va="top", fontsize=7.5, color=MUTED,
                fontproperties=BODY)
        ax.plot([0.0, 0.92], [y - 0.065, y - 0.065], transform=ax.transAxes,
                color=HAIRLINE, linewidth=0.7)


def _render_crosshair_geometry(agg: dict, path: Path,
                               figure_data: dict | None = None) -> bool:
    geometry = ((agg.get("crosshair") or {}).get("geometry") or {})
    if not any((block or {}).get("valid_n") for block in geometry.values()):
        return False
    fig = plt.figure(figsize=(13, 7.6))
    _figure_title(
        fig,
        "Crosshair geometry",
        "Observed Gap × Size combinations; bubble area is player count and labels show cells with n ≥ 2",
    )
    grid = fig.add_gridspec(2, 4, width_ratios=(1, 1, 1, 0.92),
                            left=0.07, right=0.96, bottom=0.13, top=0.86,
                            wspace=0.42, hspace=0.52)
    joint_ax = fig.add_subplot(grid[:, :3])
    joint = (figure_data or {}).get("crosshair_gap_size") or {}
    if not _render_joint_geometry(joint_ax, joint):
        joint_ax.set_visible(True)
        joint_ax.set_axis_off()
        joint_ax.text(0.0, 0.56, "Joint Gap × Size counts unavailable",
                      transform=joint_ax.transAxes, fontsize=13, color=INK,
                      fontproperties=DISPLAY_BOLD)
        joint_ax.text(0.0, 0.48,
                      "Marginal fields remain available in the report; no joint distribution is inferred.",
                      transform=joint_ax.transAxes, fontsize=8.5, color=MUTED,
                      fontproperties=BODY)

    thickness_ax = fig.add_subplot(grid[0, 3])
    thickness = geometry.get("thickness") or {}
    _share_bars(thickness_ax,
                _ordered(thickness.get("categories") or {}),
                int(thickness.get("valid_n") or 0), "Thickness",
                horizontal=True)
    summary_ax = fig.add_subplot(grid[1, 3])
    _geometry_summary(summary_ax, geometry)
    fig.savefig(path, dpi=150, metadata={"Software": "cs2-pro-settings"})
    plt.close(fig)
    return True


def _rgb_hex(key: str) -> str:
    try:
        r, g, b = (max(0, min(255, int(value))) for value in key.split(","))
    except (TypeError, ValueError):
        return MUTED
    return f"#{r:02x}{g:02x}{b:02x}"


def _active_color_rows(crosshair: dict) -> tuple[
        list[tuple[str, int, str]], int, int, int, int, int]:
    """Resolve active-color rows without merging semantically distinct modes.

    Preset labels and exact Custom RGB values share one ranking denominator,
    but remain separate rows even when their swatches look identical. Custom
    players with an incomplete RGB triplet do not enter the resolved-color
    denominator.
    """
    modes = crosshair.get("color_categories") or {}
    custom = crosshair.get("custom_rgb") or {}
    rgb_items = _ranked(custom.get("categories") or {}, top_n=10_000)
    rgb_n = int(custom.get("valid_n") or sum(count for _, count in rgb_items))
    custom_players = int(custom.get("custom_players")
                         or modes.get("Custom") or 0)

    rows = [
        (f"Preset · {label}", int(count),
         _PRESET_COLORS.get(str(label), MUTED))
        for label, count in modes.items()
        if str(label).casefold() != "custom" and int(count) > 0
    ]

    # Repeated exact RGB values form the useful ranked signal. If every exact
    # value is unique, retain the highest-count values so the figure can still
    # represent resolved observations without inventing an "other color".
    shown_rgb = [(key, count) for key, count in rgb_items if count >= 2]
    if not shown_rgb:
        shown_rgb = rgb_items[:8]
    shown_keys = {key for key, _count in shown_rgb}
    rows.extend((f"Custom · RGB {key}", count, _rgb_hex(key))
                for key, count in shown_rgb)
    rows.sort(key=lambda row: (-row[1], row[0]))

    long_tail = [(key, count) for key, count in rgb_items
                 if key not in shown_keys]
    long_tail_n = sum(count for _key, count in long_tail)
    resolved_n = sum(int(count) for label, count in modes.items()
                     if str(label).casefold() != "custom") + rgb_n
    return (rows, resolved_n, long_tail_n, len(long_tail), rgb_n,
            custom_players)


def _render_crosshair_color(agg: dict, path: Path) -> bool:
    crosshair = agg.get("crosshair") or {}
    (rows, resolved_n, long_tail_n, long_tail_unique, rgb_n,
     custom_players) = _active_color_rows(crosshair)
    if not rows or not resolved_n:
        return False

    fig, ax = plt.subplots(figsize=(12, 6.6))
    _figure_title(
        fig,
        "Crosshair color preference",
        "Resolved active colors ranked together; preset modes and exact Custom RGB remain semantically distinct",
    )
    y = list(range(len(rows)))
    shares = [count / resolved_n * 100 for _label, count, _color in rows]
    bars = ax.barh(y, shares, color=ACCENT, edgecolor=PAPER, linewidth=0.7,
                   height=0.66)
    ax.set_yticks(y, [label for label, _count, _color in rows])
    ax.tick_params(axis="y", pad=13)
    ax.invert_yaxis()
    ax.set_xlabel("Share of resolved active colors (%)")
    ax.set_title(f"Observed active-color configurations  ·  n={resolved_n}",
                 loc="left", pad=10, fontproperties=BODY_BOLD, fontsize=10)
    ax.grid(axis="x", color=GRID, linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.set_xlim(0, max(shares) * 1.25)

    y_transform = ax.get_yaxis_transform()
    for bar, share, (label, count, swatch) in zip(bars, shares, rows):
        ax.scatter(-0.018, bar.get_y() + bar.get_height() / 2, s=78,
                   marker="s", color=swatch, edgecolor=HAIRLINE,
                   linewidth=0.8, transform=y_transform, clip_on=False,
                   zorder=4)
        ax.text(share + 0.55, bar.get_y() + bar.get_height() / 2,
                f"{share:.1f}%  {count}/{resolved_n}", va="center",
                fontsize=8, color=INK, fontproperties=BODY)

    coverage = (rgb_n / custom_players * 100) if custom_players else 0.0
    fig.text(0.95, 0.94,
             f"Exact Custom RGB coverage  {rgb_n}/{custom_players} ({coverage:.1f}%)",
             ha="right", va="top", fontsize=8, color=MUTED,
             fontproperties=BODY)
    if long_tail_n:
        fig.text(0.055, 0.06,
                 f"Long tail not drawn: {long_tail_n} players across "
                 f"{long_tail_unique} additional exact Custom RGB values "
                 f"({long_tail_n / resolved_n * 100:.1f}% of resolved n).",
                 ha="left", va="bottom", fontsize=8, color=MUTED,
                 fontproperties=BODY)
    fig.text(0.055, 0.03,
             "Preset swatches follow source labels; Custom swatches use exact RGB. "
             "Matching rows are not merged.",
             ha="left", va="bottom", fontsize=8, color=MUTED,
             fontproperties=BODY)
    fig.subplots_adjust(left=0.27, right=0.94, bottom=0.18, top=0.84)
    fig.savefig(path, dpi=150, metadata={"Software": "cs2-pro-settings"})
    plt.close(fig)
    return True


def _render_radar(agg: dict, path: Path) -> bool:
    radar = agg.get("radar") or {}
    zoom = radar.get("zoom") or {}
    zoom_n = int(zoom.get("valid_n") or 0)
    centered_n = int(radar.get("centered_valid_n", radar.get("valid_n", 0)) or 0)
    if not zoom_n and not centered_n:
        return False
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
    _figure_title(fig, "Radar settings", "Panels are independent; radar zoom is shown without directional interpretation")
    _share_bars(axes[0], _ordered(zoom.get("categories") or {}, top_n=10),
                zoom_n, "Radar zoom")
    centered_share = radar.get("centered_share")
    if centered_n and centered_share is not None:
        yes = round(float(centered_share) * centered_n)
        _share_bars(axes[1], [("Enabled", yes), ("Disabled", centered_n - yes)],
                    centered_n, "Radar centered", colors=[ACCENT_2, SOFT])
    else:
        axes[1].set_visible(False)
    _finish(fig, path)
    return True


def render_all(metrics: dict, out_dir: Path) -> list[Path]:
    """Render production figures and return only files with real data."""
    agg = metrics.get("aggregate") or {}
    figure_data = metrics.get("figure_data") or {}
    out_dir.mkdir(parents=True, exist_ok=True)
    _theme()

    # Known obsolete production names are removed so future candidate runs do
    # not retain stale charts.  No file outside this explicit list is touched.
    for name in sorted(PRODUCTION_FILES | LEGACY_FILES):
        path = out_dir / name
        if path.exists():
            path.unlink()

    renderers = (
        ("mouse.png", _render_mouse),
        ("display.png", _render_display),
        ("crosshair_geometry.png", _render_crosshair_geometry),
        ("crosshair_color.png", _render_crosshair_color),
        ("radar.png", _render_radar),
    )
    written: list[Path] = []
    for filename, renderer in renderers:
        path = out_dir / filename
        if filename == "crosshair_geometry.png":
            rendered = renderer(agg, path, figure_data)
        else:
            rendered = renderer(agg, path)
        if rendered:
            written.append(path)
    return written
