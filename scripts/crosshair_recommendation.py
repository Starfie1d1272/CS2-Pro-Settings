"""Render observed templates at a common scale, raw parameter choices and RGB.

Consumes only the public review aggregate; reuses the production color chart.
"""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cs2_pro_settings import plots


def render_templates(block, output, subtitle, *, normalized):
    rows = block["combinations"][:8]
    n = block["valid_n"]
    labels = []
    for r in rows:
        geometry = " / ".join(f'{r[k]:.3f}'.rstrip('0').rstrip('.') for k in
                              ["crosshair_size", "crosshair_gap", "crosshair_thickness"])
        labels.append(geometry
                      + f'  |  dot {"on" if r["crosshair_dot"] else "off"}'
                      + f'  |  outline {r["crosshair_outline_mode"]}'
                      + f'  |  T {"on" if r["crosshair_t_style"] else "off"}'
                      + f'  |  alpha {r["crosshair_alpha"]}')
    fig, ax = plots.plt.subplots(figsize=(12, 6.4))
    plots._figure_title(fig, "Most common proportional templates" if normalized else "Most common raw parameter choices", subtitle)
    shares = [100 * r["count"] / n for r in rows]
    ax.barh(range(len(rows)), shares, color=[plots.ACCENT] + [plots.SOFT] * (len(rows)-1), height=.65)
    ax.set_yticks(range(len(rows)), labels)
    ax.invert_yaxis()
    ax.set_xlim(0, max(shares)*1.27)
    ax.set_xlabel(f"Share of comparable static-cross records (n={n})")
    ax.grid(axis="x", color=plots.GRID, alpha=.7)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    for i, (share, row) in enumerate(zip(shares, rows)):
        ax.text(share+.4, i, f'{row["count"]}/{n}  ({share:.1f}%)', va="center", fontsize=9)
    omitted = n - sum(r["count"] for r in rows)
    fig.text(.055, .095, "Labels: length / gap offset / thickness; color excluded; scope, dynamic details and outline color not extracted.", fontsize=8, color=plots.MUTED)
    fig.text(.055, .06, ("1080-height equivalents, before game pixel rounding. Counts use exact ratios; labels rounded for display." if normalized
                        else "Source pixel parameters: identical numbers across source heights do not imply identical proportional size."), fontsize=8, color=plots.MUTED)
    fig.text(.055, .025, f"Top {len(rows)} repeated templates shown; {omitted} records in remaining templates are still in the denominator.", fontsize=8, color=plots.MUTED)
    fig.subplots_adjust(left=.49, right=.93, bottom=.21, top=.8)
    fig.savefig(output, dpi=160)
    plots.plt.close(fig)


def render(review, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    plots._theme()
    sample = review["rescreened"]
    render_templates(sample["appearance"], output / "popular-templates.png",
                     f'cs2-v1 static cross / all source heights / equivalent pixels at {sample["target_height"]} / all page dates', normalized=True)
    render_templates(sample["raw_parameter_appearance"], output / "raw-parameter-templates.png",
                     'cs2-v1 static cross / all source heights / source parameter values / all page dates', normalized=False)
    rgb = review["native_colors"]
    plots._render_crosshair_color(
        {"crosshair": {"color_categories": {"Custom": rgb["valid_n"]},
                       "custom_rgb": {**rgb, "custom_players": rgb["valid_n"]}}},
        output / "native-colors.png",
        subtitle=f'cs2-v1 only / n={rgb["valid_n"]} / exact RGB / collected {review["snapshot_date"]}; page dates vary')
    return [output / name for name in ["popular-templates.png", "raw-parameter-templates.png", "native-colors.png"]]


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    review = json.loads((root / "data/aggregate/analysis/2026-10-08-crosshair.json").read_text())
    render(review, root / "figures/analysis/2026-10-08")
