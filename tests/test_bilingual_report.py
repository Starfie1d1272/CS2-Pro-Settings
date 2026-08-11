"""Bilingual snapshot report tests.

The core contract: English and Chinese reports share ONE view model, so
numbers, denominators, availability branches and section visibility cannot
drift between languages. Section visibility rules: no data -> no section;
no conflicts -> no conflict section; no real segment values -> no segments
section; first baseline -> no longitudinal comparison section.
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from cs2_pro_settings.metrics import compute_metrics  # noqa: E402
from cs2_pro_settings.models import NormalizedPlayerSettings  # noqa: E402
from cs2_pro_settings.report import (  # noqa: E402
    CURRENT_SNAPSHOT_END,
    CURRENT_SNAPSHOT_START,
    FIELD_KEYS,
    FIGURE_FILES,
    build_report_view,
    render_current_snapshot_block,
    render_report,
)

REPO = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _players(n: int, settings: bool = True) -> list[NormalizedPlayerSettings]:
    out = []
    for i in range(n):
        base = dict(player_id=f"steam:{i}", canonical_name=f"p{i}", team="vitality")
        if settings:
            base.update(
                dpi=800.0, edpi=800.0, resolution="1280x960",
                aspect_ratio="4:3", polling_rate=1000,
                crosshair_color="Custom", crosshair_dot=False,
                crosshair_outline=False, viewmodel_fov=68.0,
                radar_centered=True,
            )
        out.append(NormalizedPlayerSettings(**base))  # type: ignore[arg-type]
    return out


def _accepted_shaped_metrics(date_="2026-08-11") -> dict:
    """Mirrors the accepted 2026-08 shape: 149 cohort, 133 with settings,
    16 zero-setting, viewmodel 125, radar centered 120, refresh/fps 0."""
    players = _players(133, settings=True)
    players += _players(16, settings=False)
    metrics = compute_metrics(players, date_)
    # force the accepted per-field valid_n shape
    agg = metrics["aggregate"]
    agg["team_count"] = 30  # fixture players share one team; accepted state has 30
    agg["series"] = {"series_id": "vrs-core-v2", "cohort_semantics": "core_top30"}
    agg["scope"] = {
        "scope_id": "vrs-core-v2", "cohort_model": "vrs-core-hltv-reference-v4",
        "core_snapshot": "2026-08-10", "core_provider": "valve",
        "reference_snapshot": "2026-08-03", "reference_provider": "hltv",
        "core_team_count": 30, "reference_team_count": 30,
        "consensus_team_count": 27, "ranked_union_team_count": 33,
        "tracked_team_count": 37, "source_resolved_core_teams": 30,
        "source_unresolved_core_teams": [],
        "core_teams": [], "reference_teams": [], "consensus_teams": [],
        "ranked_union_teams": [], "tracked_teams": [],
    }
    agg["settings_availability"] = {
        "cohort_players": 149, "players_with_any_setting": 133,
        "players_with_zero_settings": 16, "any_setting_share": 0.8926,
    }
    # accepted real distributions (fixture players are homogeneous)
    agg["edpi"] = {"count": 133, "median": 800.0, "mean": 844.3,
                   "distribution": {"0-400": 0, "400-600": 13, "600-800": 32,
                                    "800-1000": 61, "1000-1200": 18,
                                    "1200-1600": 6, "1600+": 3}}
    agg["dpi"] = {"valid_n": 133, "top_category": "800",
                  "categories": {"800": 67, "400": 60, "1600": 4,
                                 "1000": 1, "3200": 1},
                  "share_800": 0.5038, "share_400": 0.4511,
                  "share_1600_plus": 0.0376}
    agg["resolution"] = {"valid_n": 133, "top_category": "1280x960",
                         "categories": {"1280x960": 91, "1920x1080": 12,
                                        "1024x768": 10, "1280x1024": 7,
                                        "1152x864": 4, "1280x768": 2,
                                        "1280x800": 2, "1440x1080": 2,
                                        "1680x1050": 2, "1350x1080": 1},
                         "share_1280x960": 0.6842}
    agg["aspect_ratio"] = {"valid_n": 133,
                           "categories": {"4:3": 109, "16:9": 11,
                                          "5:4": 8, "16:10": 5},
                           "share_4_3": 0.8195}
    agg["mouse_polling"] = {"valid_n": 133,
                            "categories": {"1000": 83, "2000": 26,
                                           "4000": 21, "8000": 3},
                            "share_4000_plus": 0.1805}
    agg["crosshair"] = {"valid_n": 133, "dot_outline_off_share": 0.8045,
                        "top_color": "Custom",
                        "color_categories": {"Custom": 60, "Blue": 35,
                                             "Green": 30, "Yellow": 8}}
    agg["viewmodel"] = {"valid_n": 125, "fov68_share": 0.912,
                        "dominant_offset": [2.5, 0.0, -1.5]}
    agg["radar"] = {"valid_n": 0, "rotating_valid_n": 0, "centered_valid_n": 120,
                    "rotating_share": None, "centered_share": 0.7167}
    agg["refresh_rate"] = {"valid_n": 0, "categories": {},
                           "share_360": None, "share_540_plus": None}
    agg["fps_max"] = {"valid_n": 0, "categories": {}, "unlimited_share": None}
    return metrics


def _self_baseline_drift(metrics: dict, date_="2026-08-11") -> dict:
    return {
        "level": 0, "changed_metrics": [],
        "cohort_change": {"baseline_players": 149, "current_players": 149,
                          "player_count_delta": 0, "added": "unavailable",
                          "removed": "unavailable"},
        "matched_panel_change": {"status": "unavailable", "matched_count": 0,
                                 "note": "no overlap"},
        "baseline_snapshot_date": date_, "current_snapshot_date": date_,
        "scope_changed": False, "cohort_stability": "unavailable",
        "roster_turnover_rate": None, "headline_suppressed": False,
        "series_compatible": True, "baseline_incompatible_reason": "",
    }


def _render_pair(metrics=None, drift=None, baseline=None, locale=None,
                 conflicts=None, segments=None):
    metrics = metrics if metrics is not None else _accepted_shaped_metrics()
    drift = drift if drift is not None else _self_baseline_drift(metrics)
    baseline = baseline if baseline is not None else metrics
    if segments is not None:
        metrics = dict(metrics)
        metrics["segments"] = segments
    kwargs = dict(
        metrics=metrics, drift=drift, source_status={"cs2settings": "ok"},
        conflicts=conflicts or [], baseline=baseline,
    )
    en = render_report(locale="en", **kwargs)
    zh = render_report(locale="zh-CN", **kwargs)
    if locale == "zh-CN":
        return zh, en
    return en, zh


# ---------------------------------------------------------------------------
# 1/2. both locales render
# ---------------------------------------------------------------------------

def test_english_report_renders():
    en, _ = _render_pair()
    assert en.startswith("# CS2 Professional Settings Snapshot")
    assert "## 1. Key numbers" in en


def test_chinese_report_renders():
    _, zh = _render_pair()
    assert zh.startswith("# CS2 职业选手设置月度快照")
    assert "## 1. 本期核心数据" in zh


# ---------------------------------------------------------------------------
# 3. bilingual numeric parity (same view model)
# ---------------------------------------------------------------------------

def test_bilingual_snapshot_values_parity():
    en, zh = _render_pair()
    for needle in ("2026-08-11", "vrs-core-v2", "30", "149",
                   "133/149", "800", "82.0%", "68.4%"):
        assert needle in en, f"missing in EN: {needle}"
        assert needle in zh, f"missing in ZH: {needle}"


def test_bilingual_field_coverage_table_parity():
    en, zh = _render_pair()
    row_re = re.compile(r"^\| [^|]+ \| (\d+) / (\d+) \|$")
    en_rows = [tuple(m.groups()) for line in en.splitlines()
               for m in [row_re.match(line)] if m]
    zh_rows = [tuple(m.groups()) for line in zh.splitlines()
               for m in [row_re.match(line)] if m]
    assert len(en_rows) == len(FIELD_KEYS) == len(zh_rows)
    assert en_rows == zh_rows  # identical (valid_n, cohort) pairs


def test_bilingual_valid_n_bounds():
    en, zh = _render_pair()
    row_re = re.compile(r"^\| [^|]+ \| (\d+) / (\d+) \|$")
    for text in (en, zh):
        for line in text.splitlines():
            m = row_re.match(line)
            if not m:
                continue
            valid_n, cohort_n = int(m.group(1)), int(m.group(2))
            assert 0 <= valid_n <= cohort_n


def test_shared_view_model_drives_both_locales():
    """Both locales are rendered from one view: same availability flags and
    same metric strings."""
    metrics = _accepted_shaped_metrics()
    kwargs = dict(metrics=metrics, drift=_self_baseline_drift(metrics),
                  source_status={"cs2settings": "ok"}, conflicts=[],
                  baseline=metrics)
    view_en = build_report_view(locale="en", **kwargs)
    view_zh = build_report_view(locale="zh-CN", **kwargs)
    for attr in ("snapshot_date", "series_id", "team_count", "player_count",
                 "players_with_any_setting", "any_setting_pct",
                 "edpi_median", "edpi_mean", "edpi_n",
                 "dpi_n", "polling_n", "aspect_n", "resolution_n",
                 "crosshair_n", "fov_n", "radar_centered_available",
                 "radar_centered_n", "field_rows", "first_snapshot",
                 "conflict_count", "segment_rows", "previous_snapshot",
                 "roster_turnover", "matched_count"):
        assert getattr(view_en, attr) == getattr(view_zh, attr), attr


# ---------------------------------------------------------------------------
# content contract: no methodology text in either locale
# ---------------------------------------------------------------------------

def test_no_methodology_or_causality_wording():
    en, zh = _render_pair()
    for banned in ("causal performance", "Prevalence", "Methodological limitations",
                   "valid sample size", "LLM"):
        assert banned not in en, f"methodology wording in EN: {banned}"
    for banned in ("竞技表现", "方法与局限", "有效样本数（valid_n）",
                   "不调用 LLM"):
        assert banned not in zh, f"methodology wording in ZH: {banned}"


def test_no_statistics_concept_explanation():
    """No 'the median splits the sample in half' style sentences."""
    en, zh = _render_pair()
    for banned in ("splits in half", "half of the players are at or below"):
        assert banned not in en
    for banned in ("一分为二", "中位数将样本"):
        assert banned not in zh


# ---------------------------------------------------------------------------
# 4. first same-series baseline: no longitudinal section, baseline marker
# ---------------------------------------------------------------------------

def test_first_baseline_has_no_longitudinal_section():
    en, zh = _render_pair()
    assert "Changes since previous snapshot" not in en
    assert "相比上期" not in zh
    assert "baseline" in en  # metadata marker
    assert "baseline" in zh


def test_first_baseline_no_strict_trend_claims():
    en, zh = _render_pair()
    for banned in ("increased", "decreased", "rose", "fell", "→"):
        assert banned not in en
    for banned in ("上升", "下降", "→"):
        assert banned not in zh


# ---------------------------------------------------------------------------
# 5. same-series previous exists -> comparison section in both locales
# ---------------------------------------------------------------------------

def _same_series_inputs():
    metrics = _accepted_shaped_metrics()
    baseline = _accepted_shaped_metrics(date_="2026-08-01")
    drift = {
        "level": 1, "changed_metrics": [
            {"conclusion": "dpi_800_share", "baseline": 0.45, "current": 0.50,
             "change_pp": 5.0, "level": 1}],
        "cohort_change": {"baseline_players": 150, "current_players": 149,
                          "player_count_delta": -1, "added": "unavailable",
                          "removed": "unavailable"},
        "matched_panel_change": {"status": "available", "matched_count": 120,
                                 "per_field": {"dpi": {"changed": 5, "compared": 90,
                                                       "missing_to_value": 2,
                                                       "value_to_missing": 1}}},
        "baseline_snapshot_date": "2026-08-01", "current_snapshot_date": "2026-08-11",
        "scope_changed": False, "cohort_stability": "stable",
        "roster_turnover_rate": 0.02, "headline_suppressed": False,
        "series_compatible": True, "baseline_incompatible_reason": "",
    }
    return metrics, drift, baseline


def test_same_series_shows_longitudinal_comparison():
    metrics, drift, baseline = _same_series_inputs()
    en, zh = _render_pair(metrics=metrics, drift=drift, baseline=baseline)
    assert "Changes since previous snapshot" in en
    assert "Previous snapshot: 2026-08-01" in en
    assert "dpi_800_share" in en
    assert "相比上期" in zh
    assert "上一期：2026-08-01" in zh
    assert "dpi_800_share" in zh
    # not the first snapshot: no baseline marker-only metadata
    assert "baseline" not in en.splitlines()[4]


# ---------------------------------------------------------------------------
# 6. valid_n=0 -> subsection hidden, no misleading stats
# ---------------------------------------------------------------------------

def test_zero_valid_n_sections_hidden():
    en, zh = _render_pair()
    # refresh / fps / radar-rotating have valid_n=0 -> no subsections
    assert "### Monitor refresh rate" not in en
    assert "### fps_max" not in en
    assert "### Radar rotating" not in en
    assert "### 显示器刷新率" not in zh
    assert "### fps_max" not in zh
    assert "### Radar rotating" not in zh
    for banned in ("360 Hz", "540 Hz", "fps_max 0", "Insufficient"):
        assert banned not in en
    for banned in ("360 Hz", "540 Hz", "`fps_max 0`", "没有足够的"):
        assert banned not in zh
    # the coverage table still shows the true valid_n (0 / 149)
    assert "| Monitor refresh rate | 0 / 149 |" in en
    assert "| 显示器刷新率 | 0 / 149 |" in zh


# ---------------------------------------------------------------------------
# 5b. extended segments: only real values; otherwise section omitted
# ---------------------------------------------------------------------------

def _fake_segments() -> dict:
    def seg(pc, tc, med):
        return {"player_count": pc, "team_count": tc,
                "edpi": {"median": med}}
    return {
        "consensus": seg(135, 27, 800.0),
        "ranked_union": seg(160, 33, 800.0),
        "core_plus_watchlist": seg(163, 33, 800.0),
        "all_tracked": seg(172, 35, 800.0),
    }


def test_segments_section_omitted_without_real_values():
    en, zh = _render_pair()
    assert "Extended segments" not in en
    assert "扩展样本" not in zh
    assert "unavailable" not in en
    assert "unavailable" not in zh


def test_segments_section_renders_real_values_only():
    en, zh = _render_pair(segments=_fake_segments())
    assert "Extended segments" in en
    assert "扩展样本" in zh
    assert "| Ranked Union | 33 | 160 | 800 |" in en
    assert "| All tracked | 35 | 172 | 800 |" in zh
    assert "unavailable" not in en
    assert "unavailable" not in zh
    assert "Watchlist + Supplemental" not in en


# ---------------------------------------------------------------------------
# 7/8. monthly candidate: four synchronized report files
# ---------------------------------------------------------------------------

@pytest.fixture
def _candidate_env(tmp_path, monkeypatch):
    import actions_common
    fake_root = tmp_path / "repo"
    (fake_root / "data" / "aggregate").mkdir(parents=True)
    (fake_root / "reports").mkdir()
    (fake_root / "figures" / "latest").mkdir(parents=True)
    work = fake_root / "work"
    work.mkdir()
    monkeypatch.setattr(actions_common, "ROOT", fake_root)
    monkeypatch.setattr(actions_common, "WORK", work)
    monkeypatch.setattr(actions_common, "AGG", fake_root / "data" / "aggregate")
    monkeypatch.setattr(actions_common, "REPORTS", fake_root / "reports")
    monkeypatch.setattr(actions_common, "FIGURES", fake_root / "figures" / "latest")
    return actions_common, work, fake_root


def _metrics_for_candidate():
    metrics = _accepted_shaped_metrics()
    metrics.pop("segments", None)
    return metrics


def test_monthly_candidate_writes_four_reports(_candidate_env):
    actions_common, work, fake_root = _candidate_env
    (work / "report-candidate.md").write_text("EN latest v1\n", encoding="utf-8")
    (work / "report-candidate.zh-CN.md").write_text("ZH latest v1\n", encoding="utf-8")
    (work / "report-candidate-monthly.md").write_text("EN monthly v1\n", encoding="utf-8")
    (work / "report-candidate-monthly.zh-CN.md").write_text("ZH monthly v1\n", encoding="utf-8")
    changed = actions_common.write_candidate_files(_metrics_for_candidate(), monthly=True)
    month = date.today().strftime("%Y-%m")
    latest_en = fake_root / "reports" / "latest.md"
    latest_zh = fake_root / "reports" / "latest.zh-CN.md"
    month_en = fake_root / "reports" / f"{month}.md"
    month_zh = fake_root / "reports" / f"{month}.zh-CN.md"
    for p in (latest_en, latest_zh, month_en, month_zh):
        assert p.exists(), p
    # latest pair and monthly pair keep their own content (cross-links and
    # figure scopes legitimately differ; they are no longer byte-identical)
    assert latest_en.read_text() == "EN latest v1\n"
    assert latest_zh.read_text() == "ZH latest v1\n"
    assert month_en.read_text() == "EN monthly v1\n"
    assert month_zh.read_text() == "ZH monthly v1\n"
    # both figure scopes are written for a monthly candidate
    assert (fake_root / "figures" / "latest" / "edpi.png").exists()
    assert (fake_root / "figures" / month / "edpi.png").exists()
    assert "data/aggregate/latest.json" in changed
    assert f"{month}.json" in changed
    assert f"figures/{month}/*" in changed
    assert not any("social" in c for c in changed)


def test_same_month_refresh_syncs_all_four(_candidate_env):
    actions_common, work, fake_root = _candidate_env
    month = date.today().strftime("%Y-%m")
    for name, text in (("report-candidate.md", "EN latest v1\n"),
                       ("report-candidate.zh-CN.md", "ZH latest v1\n"),
                       ("report-candidate-monthly.md", "EN monthly v1\n"),
                       ("report-candidate-monthly.zh-CN.md", "ZH monthly v1\n")):
        (work / name).write_text(text, encoding="utf-8")
    actions_common.write_candidate_files(_metrics_for_candidate(), monthly=True)
    # correctness-fix refresh of the SAME month
    for name, text in (("report-candidate.md", "EN latest v2\n"),
                       ("report-candidate.zh-CN.md", "ZH latest v2\n"),
                       ("report-candidate-monthly.md", "EN monthly v2\n"),
                       ("report-candidate-monthly.zh-CN.md", "ZH monthly v2\n")):
        (work / name).write_text(text, encoding="utf-8")
    actions_common.write_candidate_files(_metrics_for_candidate(), monthly=True)
    assert (fake_root / "reports" / "latest.md").read_text() == "EN latest v2\n"
    assert (fake_root / "reports" / "latest.zh-CN.md").read_text() == "ZH latest v2\n"
    assert (fake_root / "reports" / f"{month}.md").read_text() == "EN monthly v2\n"
    assert (fake_root / "reports" / f"{month}.zh-CN.md").read_text() == "ZH monthly v2\n"


def test_next_month_does_not_touch_previous_month_figures(_candidate_env):
    """A later month's candidate must never mutate an earlier month's
    figures/YYYY-MM archive."""
    actions_common, work, fake_root = _candidate_env
    for name in ("report-candidate.md", "report-candidate.zh-CN.md",
                 "report-candidate-monthly.md", "report-candidate-monthly.zh-CN.md"):
        (work / name).write_text("x\n", encoding="utf-8")
    metrics = _metrics_for_candidate()
    actions_common.write_candidate_files(metrics, monthly=True, month="2026-08")
    prev_bytes = (fake_root / "figures" / "2026-08" / "edpi.png").read_bytes()
    actions_common.write_candidate_files(metrics, monthly=True, month="2026-09")
    assert (fake_root / "figures" / "2026-09" / "edpi.png").exists()
    assert (fake_root / "figures" / "2026-08" / "edpi.png").read_bytes() == prev_bytes


def test_monthly_report_figure_links_point_to_month_scope():
    """reports/YYYY-MM.* must reference ../figures/YYYY-MM/, never latest."""
    metrics = _accepted_shaped_metrics()
    month = "2026-08"
    en = render_report(metrics, _self_baseline_drift(metrics),
                       {"cs2settings": "ok"}, [], baseline=metrics,
                       locale="en", figure_scope=month, cross_link_base=month)
    zh = render_report(metrics, _self_baseline_drift(metrics),
                       {"cs2settings": "ok"}, [], baseline=metrics,
                       locale="zh-CN", figure_scope=month, cross_link_base=month)
    assert f"../figures/{month}/edpi.png" in en
    assert f"../figures/{month}/fov.png" in zh
    assert f"[中文版](./{month}.zh-CN.md)" in en
    assert f"[English version](./{month}.md)" in zh
    assert "../figures/latest/" not in en
    assert "../figures/latest/" not in zh


def test_latest_report_figure_links_point_to_latest_scope():
    metrics = _accepted_shaped_metrics()
    en = render_report(metrics, _self_baseline_drift(metrics),
                       {"cs2settings": "ok"}, [], baseline=metrics, locale="en")
    zh = render_report(metrics, _self_baseline_drift(metrics),
                       {"cs2settings": "ok"}, [], baseline=metrics, locale="zh-CN")
    assert "../figures/latest/edpi.png" in en
    assert "../figures/latest/fov.png" in zh
    assert "[中文版](./latest.zh-CN.md)" in en
    assert "[English version](./latest.md)" in zh
    assert "../figures/2026-08/" not in en


def test_non_monthly_candidate_writes_latest_pair_only(_candidate_env):
    actions_common, work, fake_root = _candidate_env
    month = date.today().strftime("%Y-%m")
    (work / "report-candidate.md").write_text("EN v1\n", encoding="utf-8")
    (work / "report-candidate.zh-CN.md").write_text("ZH v1\n", encoding="utf-8")
    actions_common.write_candidate_files(_metrics_for_candidate(), monthly=False)
    assert (fake_root / "reports" / "latest.md").exists()
    assert (fake_root / "reports" / "latest.zh-CN.md").exists()
    assert not (fake_root / "reports" / f"{month}.md").exists()
    assert not (fake_root / "reports" / f"{month}.zh-CN.md").exists()


# ---------------------------------------------------------------------------
# 9. social/ never modified by the automated candidate writer
# ---------------------------------------------------------------------------

def test_social_untouched_by_candidate_writer(_candidate_env):
    actions_common, work, fake_root = _candidate_env
    social = fake_root / "social" / "2026-08"
    social.mkdir(parents=True)
    marker = social / "heybox-article.md"
    marker.write_text("human editorial content\n", encoding="utf-8")
    (work / "report-candidate.md").write_text("EN v1\n", encoding="utf-8")
    (work / "report-candidate.zh-CN.md").write_text("ZH v1\n", encoding="utf-8")
    actions_common.write_candidate_files(_metrics_for_candidate(), monthly=True)
    assert marker.read_text(encoding="utf-8") == "human editorial content\n"
    assert not list((fake_root / "social").rglob("*.json"))


# ---------------------------------------------------------------------------
# 10. privacy: no SteamID / player_id list / row-level settings
# ---------------------------------------------------------------------------

def test_report_never_leaks_player_identifiers():
    metrics = _accepted_shaped_metrics()
    metrics["panel"]["player_ids"] = ["steam:76561198000000000", "steam:76561198000000001"]
    metrics["panel"]["players"] = {
        "steam:76561198000000000": {"dpi": 800, "edpi": 800},
    }
    drift = _self_baseline_drift(metrics)
    for locale in ("en", "zh-CN"):
        out = render_report(metrics, drift, {"cs2settings": "ok"}, [],
                            baseline=metrics, locale=locale)
        assert "steam:" not in out
        assert "76561198" not in out


# ---------------------------------------------------------------------------
# 11. figure links resolve to real files (no broken / empty charts)
# ---------------------------------------------------------------------------

def test_figure_links_resolve(tmp_path):
    metrics = _accepted_shaped_metrics()
    scope = "testfig"
    fig_dir = tmp_path / "figures" / scope
    fig_dir.mkdir(parents=True)
    referenced = {"edpi", "dpi", "polling", "aspect_ratio", "resolution",
                  "crosshair", "viewmodel"}
    for key in referenced:
        (fig_dir / FIGURE_FILES[key]).write_bytes(b"png")
    for locale in ("en", "zh-CN"):
        out = render_report(metrics, _self_baseline_drift(metrics),
                            {"cs2settings": "ok"}, [], baseline=metrics,
                            locale=locale, figure_scope=scope)
        links = re.findall(r"!\[[^\]]*\]\(\.\./figures/" + scope + r"/([^)]+)\)", out)
        assert links, f"no figure links in {locale}"
        for link in links:
            assert (fig_dir / link).exists(), f"broken figure link: {link}"
            assert link != "refresh_rate.png", "empty refresh chart must not be referenced"
            assert link != "radar.png", "no radar figure is referenced by the template"


# ---------------------------------------------------------------------------
# 12. determinism + accepted-aggregate live render
# ---------------------------------------------------------------------------

def test_bilingual_reports_deterministic():
    metrics = _accepted_shaped_metrics()
    en1, zh1 = _render_pair(metrics=metrics)
    en2, zh2 = _render_pair(metrics=metrics)
    assert en1 == en2
    assert zh1 == zh2


def test_committed_accepted_aggregate_renders_clean():
    """The actual accepted 2026-08 aggregate must render without leftover
    placeholders, NaN, methodology wording, or broken figure links."""
    agg_path = REPO / "data" / "aggregate" / "2026-08.json"
    fig_path = REPO / "figures" / "latest"
    if not agg_path.exists() or not fig_path.is_dir():
        pytest.skip("accepted aggregate/figures not present in this checkout")
    metrics = json.loads(agg_path.read_text(encoding="utf-8"))
    drift = _self_baseline_drift(metrics)
    for locale in ("en", "zh-CN"):
        out = render_report(metrics, drift, {"cs2settings": "ok"}, [],
                            baseline=metrics, locale=locale)
        assert "{{" not in out
        assert "NaN" not in out
        assert "133/149" in out
        assert "baseline" in out
        assert "causal" not in out
        assert "竞技表现" not in out
        # every figure link resolves against the committed figures/latest
        links = re.findall(r"!\[[^\]]*\]\(\.\./figures/latest/([^)]+)\)", out)
        for link in links:
            assert (fig_path / link).exists(), f"broken committed figure: {link}"


# ---------------------------------------------------------------------------
# 13. README bilingual presence + parity
# ---------------------------------------------------------------------------

def test_readme_bilingual_presence_and_links():
    readme_en = REPO / "README.md"
    readme_zh = REPO / "README.zh-CN.md"
    assert readme_en.exists()
    assert readme_zh.exists()
    en = readme_en.read_text(encoding="utf-8")
    zh = readme_zh.read_text(encoding="utf-8")
    assert "./README.zh-CN.md" in en
    assert "./README.md" in zh


def test_readme_bilingual_key_facts_parity():
    readme_en = REPO / "README.md"
    readme_zh = REPO / "README.zh-CN.md"
    if not (readme_en.exists() and readme_zh.exists()):
        pytest.skip("bilingual README not present yet")
    en = readme_en.read_text(encoding="utf-8")
    zh = readme_zh.read_text(encoding="utf-8")
    for fact in ("2026-08-11", "vrs-core-v2", "30 teams", "149",
                 "133/149", "82.0%", "68.4%", "91.2%"):
        assert fact in en, f"missing in EN README: {fact}"
    for fact in ("2026-08-11", "vrs-core-v2", "30 支战队", "149",
                 "133/149", "82.0%", "68.4%", "91.2%"):
        assert fact in zh, f"missing in ZH README: {fact}"


# ---------------------------------------------------------------------------
# 14. dynamic top / runner-up category rendering
# ---------------------------------------------------------------------------

def test_resolution_top_flip_uses_real_top_and_share():
    """When 1920x1080 becomes the top resolution, the report must say so
    with ITS OWN share — never 1280x960's percentage."""
    metrics = _accepted_shaped_metrics()
    metrics["aggregate"]["resolution"]["categories"] = {
        "1920x1080": 91, "1280x960": 12}
    en = render_report(metrics, _self_baseline_drift(metrics),
                       {"cs2settings": "ok"}, [], baseline=metrics, locale="en")
    assert "Most common: **1920x1080**" in en
    # 91 / 103 = 88.3%; runner-up is 1280x960 at 12/103
    assert "1280x960 is next at 12/103" in en
    assert "**1280x960** (68.4%" not in en
    zh = render_report(metrics, _self_baseline_drift(metrics),
                       {"cs2settings": "ok"}, [], baseline=metrics, locale="zh-CN")
    assert "最常见：**1920x1080**" in zh
    assert "1280x960 次之" in zh


def test_aspect_runner_up_is_dynamic():
    """When 5:4 is second, '16:9 is the next tier' must NOT appear."""
    metrics = _accepted_shaped_metrics()
    metrics["aggregate"]["aspect_ratio"]["categories"] = {
        "4:3": 109, "5:4": 11, "16:9": 8}
    en = render_report(metrics, _self_baseline_drift(metrics),
                       {"cs2settings": "ok"}, [], baseline=metrics, locale="en")
    assert "5:4 is the next tier at 11/128" in en
    assert "16:9 is the next tier" not in en
    zh = render_report(metrics, _self_baseline_drift(metrics),
                       {"cs2settings": "ok"}, [], baseline=metrics, locale="zh-CN")
    assert "5:4 次之" in zh
    assert "16:9 次之" not in zh


def test_key_numbers_use_real_top_share():
    metrics = _accepted_shaped_metrics()
    metrics["aggregate"]["resolution"]["categories"] = {
        "1920x1080": 91, "1280x960": 12}
    en = render_report(metrics, _self_baseline_drift(metrics),
                       {"cs2settings": "ok"}, [], baseline=metrics, locale="en")
    # Key numbers line uses the REAL top with the REAL share (91/103)
    assert "- 1920x1080: **88.3%**" in en
    assert "- 1280x960: **68.4%**" not in en


def test_default_top_rendering_unchanged():
    """1280x960 first / 4:3 first / 16:9 second keeps the previous output."""
    metrics = _accepted_shaped_metrics()
    en = render_report(metrics, _self_baseline_drift(metrics),
                       {"cs2settings": "ok"}, [], baseline=metrics, locale="en")
    assert "Most common: **1280x960** (68.4%, n=133)" in en
    assert "1920x1080 is next at 12/133 (9.0%)." in en
    assert "- 4:3: **82.0%** (n=133)" in en
    assert "16:9 is the next tier at 11/133 (8.3%)." in en


# ---------------------------------------------------------------------------
# 15. README CURRENT_SNAPSHOT block (automation-editable region only)
# ---------------------------------------------------------------------------

def test_readme_snapshot_block_matches_aggregate():
    metrics = _accepted_shaped_metrics()
    en = render_current_snapshot_block(metrics, locale="en", first_snapshot=True)
    for fact in ("2026-08-11", "30 teams", "149 players", "133/149",
                 "89.3%", "800", "95.5%", "82.0%", "68.4%", "62.4%",
                 "18.0%", "91.2%", "first accepted"):
        assert fact in en, f"missing in EN block: {fact}"
    zh = render_current_snapshot_block(metrics, locale="zh-CN", first_snapshot=True)
    for fact in ("2026-08-11", "30 支战队", "149 名选手", "133/149",
                 "89.3%", "800", "95.5%", "82.0%", "68.4%", "62.4%",
                 "18.0%", "91.2%", "系列的首个正式基线"):
        assert fact in zh, f"missing in ZH block: {fact}"
    # takeaway + current-month archive link live INSIDE the generated block
    assert "From the current snapshot, 800 eDPI, 4:3, 1280x960 and FOV 68" in en
    assert "Monthly archive](./reports/2026-08.md)" in en
    assert "从当前快照来看，800 eDPI、4:3、1280x960 和 FOV 68" in zh
    assert "月度存档](./reports/2026-08.zh-CN.md)" in zh
    # block is fully delimited by the markers
    assert en.startswith(CURRENT_SNAPSHOT_START)
    assert en.endswith(CURRENT_SNAPSHOT_END)
    assert zh.startswith(CURRENT_SNAPSHOT_START)
    assert zh.endswith(CURRENT_SNAPSHOT_END)


def test_readme_block_update_preserves_static_prose(_candidate_env):
    """write_candidate_files updates ONLY the CURRENT_SNAPSHOT block; all
    other README prose is untouched."""
    actions_common, work, fake_root = _candidate_env
    static = "# CS2 Pro Settings Tracker\n\nStatic tagline and project intro.\n\n## Current snapshot\n\n"
    en_block = (CURRENT_SNAPSHOT_START + "\n**OLD n/a**\n" + CURRENT_SNAPSHOT_END
                + "\n\nStatic footer after the block.\n")
    zh_block = (CURRENT_SNAPSHOT_START + "\n**OLD n/a**\n" + CURRENT_SNAPSHOT_END
                + "\n\n静态结尾。\n")
    (fake_root / "README.md").write_text(static + en_block, encoding="utf-8")
    (fake_root / "README.zh-CN.md").write_text(static + zh_block, encoding="utf-8")
    (work / "report-candidate.md").write_text("EN\n", encoding="utf-8")
    (work / "report-candidate.zh-CN.md").write_text("ZH\n", encoding="utf-8")
    actions_common.write_candidate_files(_metrics_for_candidate(), monthly=False)
    en = (fake_root / "README.md").read_text(encoding="utf-8")
    zh = (fake_root / "README.zh-CN.md").read_text(encoding="utf-8")
    assert "Static tagline and project intro." in en
    assert "Static footer after the block." in en
    assert "2026-08-11" in en and "OLD n/a" not in en
    assert "静态结尾。" in zh
    assert "2026-08-11" in zh and "OLD n/a" not in zh


def test_readme_without_block_is_untouched(_candidate_env):
    """A README without the markers must never be modified."""
    actions_common, work, fake_root = _candidate_env
    (fake_root / "README.md").write_text("no block here\n", encoding="utf-8")
    (work / "report-candidate.md").write_text("EN\n", encoding="utf-8")
    (work / "report-candidate.zh-CN.md").write_text("ZH\n", encoding="utf-8")
    actions_common.write_candidate_files(_metrics_for_candidate(), monthly=False)
    assert (fake_root / "README.md").read_text(encoding="utf-8") == "no block here\n"


def test_readme_next_month_leaves_no_stale_snapshot_content(_candidate_env):
    """Simulating the 2026-09 update: the READMEs must contain NO residual
    `reports/2026-08` archive link and NO old snapshot-specific takeaway —
    the whole current-snapshot region (numbers, takeaway, links) is
    regenerated from the new aggregate."""
    actions_common, work, fake_root = _candidate_env
    # seed with the CURRENT committed READMEs (they contain the 2026-08
    # archive link and the old takeaway, exactly like the pre-update state)
    en_seed = (REPO / "README.md").read_text(encoding="utf-8")
    zh_seed = (REPO / "README.zh-CN.md").read_text(encoding="utf-8")
    assert "reports/2026-08.md" in en_seed and "reports/2026-08.zh-CN.md" in zh_seed
    (fake_root / "README.md").write_text(en_seed, encoding="utf-8")
    (fake_root / "README.zh-CN.md").write_text(zh_seed, encoding="utf-8")
    for name in ("report-candidate.md", "report-candidate.zh-CN.md",
                 "report-candidate-monthly.md", "report-candidate-monthly.zh-CN.md"):
        (work / name).write_text("x\n", encoding="utf-8")
    # 2026-09 data with DIFFERENT top categories / median
    metrics = _accepted_shaped_metrics(date_="2026-09-10")
    agg = metrics["aggregate"]
    agg["edpi"]["median"] = 900.0
    agg["dpi"]["categories"] = {"1600": 80, "800": 40, "400": 10}
    agg["aspect_ratio"]["categories"] = {"16:9": 100, "4:3": 30}
    agg["resolution"]["categories"] = {"1920x1080": 100, "1280x960": 30}
    agg["mouse_polling"]["categories"] = {"2000": 80, "1000": 40, "4000": 10}
    actions_common.write_candidate_files(metrics, monthly=True, month="2026-09")
    en = (fake_root / "README.md").read_text(encoding="utf-8")
    zh = (fake_root / "README.zh-CN.md").read_text(encoding="utf-8")
    # no stale month link anywhere in either README
    assert "reports/2026-08" not in en, "stale 2026-08 archive link in EN"
    assert "reports/2026-08" not in zh, "stale 2026-08 archive link in ZH"
    # the new month's archive link is generated
    assert "./reports/2026-09.md" in en
    assert "./reports/2026-09.zh-CN.md" in zh
    # old snapshot-specific takeaway (named 800 eDPI / 4:3 / 1280x960) gone
    for stale in ("800 eDPI, 4:3, 1280x960", "800 eDPI、4:3、1280×960",
                  "800 eDPI、4:3、1280x960"):
        assert stale not in en and stale not in zh, f"stale takeaway: {stale}"
    # the new takeaway reflects the 2026-09 top categories
    assert "900 eDPI, 16:9, 1920x1080" in en
    assert "900 eDPI、16:9、1920x1080" in zh
    assert "2026-09-10" in en and "2026-09-10" in zh


# ---------------------------------------------------------------------------
# 16. render_accepted.py backfill guards
# ---------------------------------------------------------------------------

def _patch_render_accepted(tmp_path, monkeypatch):
    import render_accepted
    monkeypatch.setattr(render_accepted, "REPORTS_DIR", tmp_path / "reports")
    (tmp_path / "reports").mkdir(parents=True)
    return render_accepted


def test_render_accepted_refuses_legacy_month(tmp_path, monkeypatch):
    render_accepted = _patch_render_accepted(tmp_path, monkeypatch)
    with pytest.raises(SystemExit):
        render_accepted.main(["--month", "2026-05"])


def test_render_accepted_bare_invocation_rejected(tmp_path, monkeypatch):
    """No --month: the one-time backfill tool must refuse to do anything
    (it must never re-render latest.* from a self-baseline)."""
    render_accepted = _patch_render_accepted(tmp_path, monkeypatch)
    with pytest.raises(SystemExit):
        render_accepted.main([])
    assert not (tmp_path / "reports" / "latest.md").exists()
    assert not (tmp_path / "reports" / "latest.zh-CN.md").exists()


def test_render_accepted_rejects_future_month(tmp_path, monkeypatch):
    """Any month other than the first-baseline month is rejected, so the
    tool can never be (mis)used for a future report."""
    render_accepted = _patch_render_accepted(tmp_path, monkeypatch)
    with pytest.raises(SystemExit):
        render_accepted.main(["--month", "2026-09"])
    assert not (tmp_path / "reports" / "2026-09.md").exists()
    assert not (tmp_path / "reports" / "2026-09.zh-CN.md").exists()


def test_render_accepted_month_writes_archive_only(tmp_path, monkeypatch):
    render_accepted = _patch_render_accepted(tmp_path, monkeypatch)
    assert render_accepted.main(["--month", "2026-08"]) == 0
    assert (tmp_path / "reports" / "2026-08.md").exists()
    assert (tmp_path / "reports" / "2026-08.zh-CN.md").exists()
    # archive-only backfill must NEVER touch reports/latest.*
    assert not (tmp_path / "reports" / "latest.md").exists()
    assert not (tmp_path / "reports" / "latest.zh-CN.md").exists()


def test_render_accepted_never_overwrites_future_latest(tmp_path, monkeypatch):
    """A committed future latest.* must survive a backfill run untouched."""
    render_accepted = _patch_render_accepted(tmp_path, monkeypatch)
    (tmp_path / "reports" / "latest.md").write_text(
        "FUTURE LATEST CONTENT\n", encoding="utf-8")
    (tmp_path / "reports" / "latest.zh-CN.md").write_text(
        "未来最新报告内容\n", encoding="utf-8")
    assert render_accepted.main(["--month", "2026-08"]) == 0
    assert (tmp_path / "reports" / "latest.md").read_text(
        encoding="utf-8") == "FUTURE LATEST CONTENT\n"
    assert (tmp_path / "reports" / "latest.zh-CN.md").read_text(
        encoding="utf-8") == "未来最新报告内容\n"
