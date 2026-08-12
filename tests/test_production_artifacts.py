"""Committed production-artifact contracts for the reporting closeout."""
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_legacy_may_artifacts_remain_byte_identical():
    expected = {
        "data/aggregate/2026-05.json":
            "e94f8fd84f0c7610d909438b6ef2459309aea75377cbb800029a1fc391a045b8",
        "reports/2026-05.md":
            "fe2d65d3db87f9255c3b2eec1070f2e7bda3d97597d50269a32fe9e3f77c901c",
        "config/cohort-2026-05-legacy.yaml":
            "021eb301a92bba9319d6c8569b37b8dde48fd39f31be1084e38c80c4d02b8bc3",
    }
    for relative, digest in expected.items():
        assert _sha256(ROOT / relative) == digest, relative


def test_accepted_august_monthly_latest_sync_and_identity():
    month = ROOT / "data" / "aggregate" / "2026-08.json"
    latest = ROOT / "data" / "aggregate" / "latest.json"
    assert month.read_bytes() == latest.read_bytes()
    payload = json.loads(month.read_text(encoding="utf-8"))
    aggregate = payload["aggregate"]
    assert aggregate["snapshot_date"] == "2026-08-11"
    assert aggregate["series"] == {
        "series_id": "vrs-core-v2", "cohort_semantics": "core_top30"}
    assert aggregate["scope"]["scope_id"] == "vrs-core-v2"
    assert aggregate["player_count"] == 149
    assert aggregate["team_count"] == 30
    assert aggregate["scaling_mode"]["valid_n"] == 133
    assert aggregate["zoom_sensitivity"]["valid_n"] == 132
    assert aggregate["boost_player"]["valid_n"] == 101
    assert aggregate["boost_player"]["missing_n"] == 48
    assert aggregate["crosshair"]["geometry"]["style"]["valid_n"] == 133
    assert aggregate["radar"]["zoom"]["valid_n"] == 99
    assert aggregate["edpi"]["consistency_qc"]["anomaly_count"] == 2


def test_all_committed_report_figure_links_resolve():
    for report_name in ("latest.md", "latest.zh-CN.md", "2026-08.md",
                        "2026-08.zh-CN.md"):
        report = ROOT / "reports" / report_name
        text = report.read_text(encoding="utf-8")
        links = re.findall(r"!\[[^\]]*\]\((\.\./figures/[^)]+)\)", text)
        assert links, report_name
        for link in links:
            assert (report.parent / link).resolve().is_file(), (report_name, link)
