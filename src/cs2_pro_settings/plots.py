"""Headline metric figures (deterministic, matplotlib only).

Migrates the most important chart logic from notebooks/v1/03_final_report.ipynb:
eDPI, DPI, resolution, refresh rate, crosshair color, FOV, radar, polling rate.

Output: figures/latest/*.png — no AI-generated images.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

DARK_BG = "#0d0d0d"
ACCENT = "#00ff66"
CYAN = "#00e5ff"
MAGENTA = "#ff00ff"
ORANGE = "#ff4500"


def _theme() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": DARK_BG,
            "axes.facecolor": DARK_BG,
            "savefig.facecolor": DARK_BG,
            "axes.edgecolor": "#333333",
            "axes.labelcolor": "#cccccc",
            "text.color": "#cccccc",
            "xtick.color": "#999999",
            "ytick.color": "#999999",
            "axes.grid": True,
            "grid.color": "#222222",
            "grid.alpha": 0.6,
            "font.size": 10,
        }
    )


def _counts(values: list) -> dict:
    out: dict = {}
    for v in values:
        if v is None:
            continue
        key = int(v) if isinstance(v, float) and v.is_integer() else v
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], str(kv[0]))))


def _bar(ax, cats: dict, title: str, color: str, ylabel: str = "Player Count") -> None:
    labels = [str(k) for k in cats]
    counts = list(cats.values())
    ax.bar(labels, counts, color=color, edgecolor="#121212", linewidth=1.2)
    ax.set_title(title, fontsize=13, fontweight="bold", color=color, pad=12)
    ax.set_ylabel(ylabel)
    for i, c in enumerate(counts):
        ax.text(i, c + 0.3, str(c), ha="center", fontsize=9, color="#bbbbbb")
    ax.set_xticklabels(labels, rotation=30, ha="right")


_EDPI_BIN_RANGES = [
    ("0-400", 0, 400), ("400-600", 400, 600), ("600-800", 600, 800),
    ("800-1000", 800, 1000), ("1000-1200", 1000, 1200), ("1200-1600", 1200, 1600),
    ("1600+", 1600, float("inf")),
]


def render_all(metrics: dict, out_dir: Path) -> list[Path]:
    """Render the headline figures; returns the written paths."""
    agg = metrics["aggregate"]
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    _theme()

    # eDPI distribution (histogram + median line)
    edpi = agg.get("edpi") or {}
    dist = edpi.get("distribution") or {}
    fig, ax = plt.subplots(figsize=(9, 5))
    labels = list(dist.keys())
    counts = list(dist.values())
    ax.bar(labels, counts, color=ACCENT, edgecolor="#121212")
    med = edpi.get("median")
    # median marker: draw the line at the histogram bin that CONTAINS the
    # current median (not a hard-coded 800-1000 bin)
    if med is not None:
        median_bin = None
        for label, lo, hi in _EDPI_BIN_RANGES:
            if lo <= med < hi:
                median_bin = label
                break
        if median_bin and median_bin in labels:
            ax.axvline(labels.index(median_bin), color=MAGENTA,
                       linestyle="--", alpha=0.7)
    ax.set_title(f"eDPI Distribution (median {med}, mean {edpi.get('mean')})",
                 fontsize=13, fontweight="bold", color=ACCENT)
    ax.set_ylabel("Player Count")
    fig.tight_layout()
    p = out_dir / "edpi.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    written.append(p)

    # DPI
    fig, ax = plt.subplots(figsize=(9, 5))
    _bar(ax, {k: v for k, v in ((agg.get("dpi") or {}).get("categories") or {}).items()},
         "DPI Distribution", ACCENT)
    p = out_dir / "dpi.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    written.append(p)

    # Resolution
    fig, ax = plt.subplots(figsize=(10, 5))
    _bar(ax, dict(list(((agg.get("resolution") or {}).get("categories") or {}).items())[:10]), "Resolution (top 10)", CYAN)
    p = out_dir / "resolution.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    written.append(p)

    # Refresh rate
    fig, ax = plt.subplots(figsize=(9, 5))
    _bar(ax, {k: v for k, v in ((agg.get("refresh_rate") or {}).get("categories") or {}).items()}, "Monitor Refresh Rate", ORANGE)
    p = out_dir / "refresh_rate.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    written.append(p)

    # Crosshair color
    fig, ax = plt.subplots(figsize=(9, 5))
    _bar(ax, (agg.get("crosshair") or {}).get("color_categories") or {}, "Crosshair Color", MAGENTA)
    p = out_dir / "crosshair_color.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    written.append(p)

    # FOV
    fig, ax = plt.subplots(figsize=(8, 5))
    vm = agg.get("viewmodel") or {}
    fov68_share = vm.get("fov68_share") or 0.0
    ax.bar(["FOV 68", "Other"],
           [fov68_share * vm.get("valid_n", 0), (1 - fov68_share) * vm.get("valid_n", 0)],
           color=[ACCENT, "#555555"], edgecolor="#121212")
    ax.set_title(f"Viewmodel FOV (68 share {fov68_share * 100:.1f}%, n={vm.get('valid_n', 0)})",
                 fontsize=13, fontweight="bold", color=ACCENT)
    ax.set_ylabel("Player Count")
    fig.tight_layout()
    p = out_dir / "fov.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    written.append(p)

    # Radar: rotating and centered have INDEPENDENT denominators
    radar = agg.get("radar") or {}
    rot_valid = radar.get("rotating_valid_n", radar.get("valid_n", 0))
    cent_valid = radar.get("centered_valid_n", radar.get("valid_n", 0))
    rot_share = radar.get("rotating_share") or 0.0
    cent_share = radar.get("centered_share") or 0.0
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(["Rotating", "Centered"],
           [rot_share * rot_valid, cent_share * cent_valid],
           color=[CYAN, ACCENT], edgecolor="#121212")
    ax.set_title(f"Radar preferences (rotating n={rot_valid}, centered n={cent_valid})",
                 fontsize=13, fontweight="bold", color=CYAN)
    ax.set_ylabel("Player Count")
    fig.tight_layout()
    p = out_dir / "radar.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    written.append(p)

    # Polling rate
    fig, ax = plt.subplots(figsize=(9, 5))
    _bar(ax, {k: v for k, v in ((agg.get("mouse_polling") or {}).get("categories") or {}).items()}, "Mouse Polling Rate", CYAN)
    p = out_dir / "polling_rate.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    written.append(p)

    return written
