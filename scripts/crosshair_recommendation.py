"""Render popular observed appearance combinations and exact RGB preferences.

Consumes only the public review aggregate; reuses the production color chart.
"""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cs2_pro_settings import plots


def render(review, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    plots._theme()
    block = review["popular_appearance"]
    rows = block["combinations"]
    n = block["valid_n"]
    # This is a full extracted appearance tuple, not a projection or cluster.
    labels = []
    for r in rows:
        labels.append(f'{r["crosshair_size"]:g} / {r["crosshair_gap"]:g} / {r["crosshair_thickness"]:g}'
                      + f'  |  dot {"on" if r["crosshair_dot"] else "off"}'
                      + f'  |  outline {r["crosshair_outline_mode"]}'
                      + f'  |  T {"on" if r["crosshair_t_style"] else "off"}'
                      + f'  |  alpha {r["crosshair_alpha"]}')
    fig, ax = plots.plt.subplots(figsize=(12, 5.8))
    plots._figure_title(fig, "Most common observed crosshair templates",
                        f'cs2-v1 static cross / reference height {block["reference_height"]} / October page verification')
    shares = [100 * r["count"] / n for r in rows]
    ax.barh(range(len(rows)), shares, color=[plots.ACCENT] + [plots.SOFT] * (len(rows)-1), height=.65)
    ax.set_yticks(range(len(rows)), labels)
    ax.invert_yaxis()
    ax.set_xlim(0, max(shares)*1.23)
    ax.set_xlabel(f"Share of complete extracted appearance records (n={n})")
    ax.grid(axis="x", color=plots.GRID, alpha=.7)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    for i, (share, row) in enumerate(zip(shares, rows)):
        ax.text(share+.5, i, f'{row["count"]}/{n}  ({share:.1f}%)', va="center", fontsize=9)
    fig.text(.055, .08, "Labels: length / gap offset / thickness in source pixels; gap offset is not the center-hole width.", fontsize=8, color=plots.MUTED)
    fig.text(.055, .045, f'Colors excluded; {block["singleton_n"]} singleton templates omitted. Scope, dynamic details and outline color not extracted.', fontsize=8, color=plots.MUTED)
    fig.subplots_adjust(left=.48, right=.93, bottom=.19, top=.8)
    fig.savefig(output / "popular-templates.png", dpi=160)
    plots.plt.close(fig)
    rgb = review["native_colors"]
    plots._render_crosshair_color(
        {"crosshair": {"color_categories": {"Custom": rgb["valid_n"]},
                       "custom_rgb": {**rgb, "custom_players": rgb["valid_n"]}}},
        output / "native-colors.png",
        subtitle=f'cs2-v1 only / n={rgb["valid_n"]} / exact RGB / collected {review["snapshot_date"]}; page dates vary')
    return [output / name for name in ["popular-templates.png", "native-colors.png"]]


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    review = json.loads((root / "data/aggregate/analysis/2026-10-08-crosshair.json").read_text())
    render(review, root / "figures/analysis/2026-10-08")
