"""Lightweight tests for the social/editorial figure style module.

These cover the presentation primitives only — no data, no analysis.
The real acceptance test for the module is the visual regression of the
AWPer × eDPI figure (work/analysis/awper-edpi/, gitignored).
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless-safe for CI

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

from scripts.social import editorial_style as es  # noqa: E402


@pytest.fixture(autouse=True)
def _close_figs():
    yield
    plt.close("all")


def _rgba(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)) + (1.0,)


def test_setup_editorial_typography_is_idempotent():
    es.setup_editorial_typography()
    before = list(es._REGISTERED_FONT_PATHS)
    es.setup_editorial_typography()
    assert list(es._REGISTERED_FONT_PATHS) == before
    assert plt.rcParams["axes.unicode_minus"] is False


def test_create_editorial_figure_applies_background_and_axes_style():
    fig, ax = es.create_editorial_figure()
    assert fig is not None and ax is not None
    assert fig.patch.get_facecolor() == _rgba(es.FIG_BG)
    assert ax.get_facecolor() == _rgba(es.FIG_BG)
    assert ax.spines["top"].get_visible() is False
    assert ax.spines["right"].get_visible() is False
    assert ax.spines["left"].get_edgecolor() == _rgba(es.SPINE)
    assert ax.get_axisbelow() is True
    # horizontal grid only
    assert any(gl.get_visible() for gl in ax.get_ygridlines())
    assert not any(gl.get_visible() for gl in ax.get_xgridlines())


def test_create_editorial_figure_rejects_bad_grid_axis():
    with pytest.raises(ValueError):
        es.create_editorial_figure(grid_axis="diagonal")


def test_add_editorial_header_title_subtitle():
    fig, ax = es.create_editorial_figure()
    title_t, sub_t, leg = es.add_editorial_header(fig, "TITLE", "SUBTITLE")
    assert title_t.get_text() == "TITLE"
    assert sub_t.get_text() == "SUBTITLE"
    assert leg is None
    texts = [t.get_text() for t in fig.texts]
    assert "TITLE" in texts
    assert "SUBTITLE" in texts
    assert fig.legends == []


def test_add_editorial_header_legend():
    fig, ax = es.create_editorial_figure()
    handles = [es.legend_handle(es.ACCENT_WARM, "A"), es.legend_handle(es.ACCENT_COOL, "B")]
    _title_t, _sub_t, leg = es.add_editorial_header(fig, "T", "S", legend_handles=handles)
    assert leg is not None
    assert len(fig.legends) == 1
    labels = [t.get_text() for t in fig.legends[0].get_texts()]
    assert labels == ["A", "B"]


def test_add_editorial_footer():
    fig, ax = es.create_editorial_figure()
    footer = es.add_editorial_footer(fig, "footer text")
    assert footer.get_text() == "footer text"
    assert "footer text" in [t.get_text() for t in fig.texts]


def test_add_corner_pill_left_and_right():
    fig, ax = es.create_editorial_figure()
    left_pill = es.add_corner_pill(ax, "LEFT", side="left")
    right_pill = es.add_corner_pill(ax, "RIGHT", side="right")
    assert left_pill.get_ha() == "left"
    assert right_pill.get_ha() == "right"


def test_add_corner_pill_rejects_bad_side():
    fig, ax = es.create_editorial_figure()
    with pytest.raises(ValueError):
        es.add_corner_pill(ax, "X", side="top")


def test_style_muted_and_highlight_points_and_reference_line():
    fig, ax = es.create_editorial_figure()
    muted = es.style_muted_points(ax, [1, 2, 3], [4, 5, 6])
    hi = es.style_highlight_points(ax, [2], [5], es.ACCENT_WARM)
    assert len(ax.collections) == 2
    assert muted.get_offsets().shape == (3, 2)
    assert hi.get_offsets().shape == (1, 2)
    hline = es.add_reference_line(ax, 800, label="baseline 800")
    vline = es.add_reference_line(ax, 2, orientation="vertical", label="cutoff")
    assert hline.get_ydata()[0] == 800
    assert vline.get_xdata()[0] == 2
    assert any(t.get_text() == "baseline 800" for t in ax.texts)
    assert any(t.get_text() == "cutoff" for t in ax.texts)


def test_add_reference_line_rejects_bad_orientation():
    fig, ax = es.create_editorial_figure()
    with pytest.raises(ValueError):
        es.add_reference_line(ax, 100, orientation="diagonal")


def test_editorial_annotate_with_and_without_leader():
    fig, ax = es.create_editorial_figure()
    a1 = es.editorial_annotate(
        ax, (0.5, 1000), "label", es.ACCENT_WARM, xytext=(10, 10), ha="left", va="bottom"
    )
    a2 = es.editorial_annotate(
        ax, (0.6, 1000), "lead", es.ACCENT_COOL, xytext=(20, 20), leader=True
    )
    assert a1.get_text() == "label"
    assert a2.get_text() == "lead"


def test_legend_handle_builds_line2d():
    h = es.legend_handle(es.ACCENT_WARM, "X", size=9, alpha=0.5)
    assert h.get_label() == "X"
    from matplotlib.colors import to_rgba

    assert to_rgba(h.get_markerfacecolor()) == _rgba(es.ACCENT_WARM)
    assert h.get_alpha() == 0.5


def test_save_editorial_figure_exports_and_closes(tmp_path):
    fig, _ax = es.create_editorial_figure()
    out = es.save_editorial_figure(
        fig, tmp_path / "nested" / "chart", formats=("png", "svg"), dpi=100, close=True
    )
    assert [p.suffix for p in out] == [".png", ".svg"]
    assert all(p.exists() and p.stat().st_size > 0 for p in out)
