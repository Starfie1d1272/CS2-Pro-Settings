"""Social / editorial figure visual style layer (CS2 Pro Settings).

This module is the *presentation* layer for social/editorial data figures —
article and community-facing graphics (Heybox articles, social posts) that
follow the HLTV-style editorial hierarchy:

- strong title / subtitle hierarchy, generous plot area
- muted background points, highlighted key players
- fixed deep blue-grey editorial palette and typography
- header legend, corner pills, footer, reference lines

It is NOT part of the production plotting pipeline (``cs2_pro_settings.plots``)
and contains no analysis logic. Each figure script owns its own data loading,
sample selection, variables, annotations, and story; this module only provides
reusable presentation primitives so the next social figure keeps the same
visual language without copying boilerplate.

Usage (from the repo root)::

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path.cwd()))
    from scripts.social.editorial_style import (
        setup_editorial_typography, create_editorial_figure,
        add_editorial_header, add_editorial_footer, add_corner_pill,
        style_muted_points, add_reference_line, editorial_annotate,
        legend_handle,
    )
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D

# ---------------------------------------------------------------------------
# Style tokens — palette (semantic-neutral; map to your story per figure)
# ---------------------------------------------------------------------------

FIG_BG = "#303C49"          # figure + axes background (deep blue-grey)
TEXT_PRIMARY = "#E7EDF3"     # titles, axis labels, legend text
TEXT_SECONDARY = "#B7C0C9"   # subtitle, tick labels, pill text
TEXT_MUTED = "#8F9AA5"       # footer, overflow notes, pill outline

GRID = "#52606D"             # horizontal gridlines
SPINE = "#64717D"            # axis spines
POINT_MUTED = "#91A0AE"      # muted background points

ACCENT_WARM = "#F47A45"      # warm accent (e.g. highlighted AWPers)
ACCENT_COOL = "#68A7DE"      # cool accent (e.g. rifle comparison group)
REFERENCE = "#AAB4BE"        # reference line (e.g. eDPI = 800)
NEUTRAL_WHITE = "#F7F9FB"    # neutral outline / highlight edge

# ---------------------------------------------------------------------------
# Style tokens — typography
# ---------------------------------------------------------------------------

TITLE_FONT_SIZE = 30
SUBTITLE_FONT_SIZE = 13
AXIS_LABEL_FONT_SIZE = 13
TICK_FONT_SIZE = 11
LEGEND_FONT_SIZE = 11
ANNOTATION_FONT_SIZE = 10.5
FOOTER_FONT_SIZE = 9.8
PILL_FONT_SIZE = 10.5
REFERENCE_TEXT_FONT_SIZE = 10.5

TITLE_FONT_WEIGHT = "bold"

# ---------------------------------------------------------------------------
# Style tokens — layout (figure coordinates; figure fraction for corner pills)
# ---------------------------------------------------------------------------

FIG_SIZE = (12.8, 9.6)                       # ~4:3 editorial canvas
MARGINS = dict(left=0.085, right=0.975, bottom=0.135, top=0.785)

HEADER_TITLE_POS = (0.085, 0.935)            # figure coords, ha=left, va=top
HEADER_SUBTITLE_POS = (0.085, 0.895)         # figure coords, ha=left, va=top
HEADER_LEGEND_ANCHOR = (0.083, 0.858)        # fig.legend bbox_to_anchor
FOOTER_POS = (0.085, 0.058)                  # figure coords, ha=left, va=bottom

PILL_TOP = 0.965                             # axes fraction (top edge)
PILL_LEFT_X = 0.012                          # axes fraction, ha=left
PILL_RIGHT_X = 0.988                         # axes fraction, ha=right

# ---------------------------------------------------------------------------
# Typography setup (CJK-capable, silent fallback on systems without these
# fonts — CI / headless Linux just uses the sans-serif fallback chain).
# ---------------------------------------------------------------------------

_CJK_FONT_CANDIDATES = (
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
)


def setup_editorial_typography() -> None:
    """Register CJK fonts if present and set the editorial font family.

    Call once per figure script, before creating any figure.
    """
    for fp in _CJK_FONT_CANDIDATES:
        if Path(fp).exists():
            font_manager.fontManager.addfont(fp)
    plt.rcParams["font.family"] = [
        "PingFang SC",
        "Hiragino Sans GB",
        "Heiti SC",
        "Arial Unicode MS",
        "sans-serif",
    ]
    plt.rcParams["axes.unicode_minus"] = False


# ---------------------------------------------------------------------------
# Figure / axes primitives
# ---------------------------------------------------------------------------

def create_editorial_figure(figsize=FIG_SIZE, margins=None):
    """Create a figure + axes with the editorial background, margins,
    spines, ticks and horizontal grid applied.

    Returns ``(fig, ax)``. No titles, ranges or data are set here.
    """
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(FIG_BG)
    ax.set_facecolor(FIG_BG)
    fig.subplots_adjust(**(margins if margins is not None else MARGINS))

    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(SPINE)
        ax.spines[side].set_linewidth(0.9)

    ax.tick_params(colors=TEXT_SECONDARY, labelsize=TICK_FONT_SIZE,
                   length=3.5, width=0.8)
    ax.grid(axis="y", color=GRID, linewidth=0.8, alpha=0.45)
    ax.set_axisbelow(True)

    return fig, ax


def add_editorial_header(fig, title, subtitle, legend_handles=None):
    """Place the big left-aligned title, one-line subtitle, and (optional)
    horizontal header legend.

    ``legend_handles`` is a list of matplotlib handles (see ``legend_handle``);
    the legend is laid out in a single row under the subtitle.
    """
    fig.text(
        *HEADER_TITLE_POS,
        title,
        fontsize=TITLE_FONT_SIZE,
        fontweight=TITLE_FONT_WEIGHT,
        color=TEXT_PRIMARY,
        ha="left",
        va="top",
    )
    fig.text(
        *HEADER_SUBTITLE_POS,
        subtitle,
        fontsize=SUBTITLE_FONT_SIZE,
        color=TEXT_SECONDARY,
        ha="left",
        va="top",
    )
    if legend_handles:
        fig.legend(
            handles=legend_handles,
            loc="upper left",
            bbox_to_anchor=HEADER_LEGEND_ANCHOR,
            ncol=len(legend_handles),
            frameon=False,
            fontsize=LEGEND_FONT_SIZE,
            labelcolor=TEXT_PRIMARY,
            handletextpad=0.5,
            columnspacing=1.6,
            borderaxespad=0,
        )


def add_editorial_footer(fig, text):
    """Place the muted footer line (data notes / provenance, natural
    language — no internal field names)."""
    fig.text(
        *FOOTER_POS,
        text,
        fontsize=FOOTER_FONT_SIZE,
        color=TEXT_MUTED,
        ha="left",
        va="bottom",
    )


def add_corner_pill(ax, text, side="left", y=PILL_TOP):
    """Add a lightweight outlined, italic corner hint (e.g. "步枪为主" /
    "主狙职责"). ``side`` is ``"left"`` or ``"right"`` (axes fraction coords).
    """
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")
    x = PILL_LEFT_X if side == "left" else PILL_RIGHT_X
    ha = "left" if side == "left" else "right"
    pill = dict(
        boxstyle="round,pad=0.34,rounding_size=0.28",
        facecolor="none",
        edgecolor=TEXT_MUTED,
        linewidth=0.9,
    )
    ax.text(
        x,
        y,
        text,
        transform=ax.transAxes,
        fontsize=PILL_FONT_SIZE,
        fontstyle="italic",
        color=TEXT_SECONDARY,
        ha=ha,
        va="top",
        bbox=pill,
    )


# ---------------------------------------------------------------------------
# Element styling helpers
# ---------------------------------------------------------------------------

def style_muted_points(ax, xs, ys, s=22, alpha=0.28, zorder=1):
    """Background cloud of low-emphasis points (all other players)."""
    ax.scatter(xs, ys, s=s, c=POINT_MUTED, alpha=alpha,
               linewidths=0, zorder=zorder)


def add_reference_line(ax, y, color=REFERENCE, linewidth=1.15,
                       linestyle=(0, (5, 5)), alpha=0.95, zorder=2):
    """A restrained horizontal reference line (e.g. eDPI = 800)."""
    ax.axhline(y, color=color, linewidth=linewidth, linestyle=linestyle,
               alpha=alpha, zorder=zorder)


def editorial_annotate(ax, xy, text, color, *, xytext, ha="left", va="center",
                       fontsize=ANNOTATION_FONT_SIZE, bold=False, leader=False):
    """Annotate a highlighted point: offset-points placement, per-figure
    colors, optional short leader line. Coordinates are the caller's job."""
    arrowprops = None
    if leader:
        arrowprops = dict(
            arrowstyle="-",
            color=TEXT_SECONDARY,
            linewidth=0.85,
            shrinkA=3,
            shrinkB=4,
        )
    ax.annotate(
        text,
        xy=xy,
        xycoords="data",
        xytext=xytext,
        textcoords="offset points",
        color=color,
        fontsize=fontsize,
        fontweight="bold" if bold else "normal",
        ha=ha,
        va=va,
        arrowprops=arrowprops,
        zorder=8,
    )


def legend_handle(color, label, size=8.5, alpha=1.0, edgecolor="none"):
    """Build a single legend handle (filled dot) for header legends."""
    return Line2D(
        [], [], marker="o", linestyle="",
        markersize=size,
        markerfacecolor=color,
        markeredgecolor=edgecolor,
        alpha=alpha,
        label=label,
    )
