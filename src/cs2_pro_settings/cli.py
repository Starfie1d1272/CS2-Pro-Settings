"""Command-line interface.

Commands:
    audit-sources   check access policy for configured sources
    collect         fetch players from enabled sources
    normalize       normalize raw observations
    reconcile       merge multi-source observations (no silent overwrite)
    metrics         compute deterministic aggregate metrics
    drift           compare current metrics against the accepted baseline
    report          render reports/latest.md (--candidate -> work/)
    update          audit -> collect -> normalize -> reconcile -> metrics
                    -> drift -> report candidate

Options:
    --offline       use test fixtures instead of the network
    --source NAME   restrict to one source
    --scheduled     restrict to sources enabled_for_schedule (workflows)
    --players a,b   restrict collection to named players
    --baseline PATH baseline aggregate (default data/aggregate/latest.json)

The pipeline NEVER falls back to a disabled source.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Optional

import yaml

from .drift import DriftReport, compute_drift, load_conclusions
from .identity import IdentityIndex
from .metrics import compute_metrics, public_aggregate
from .models import NormalizedPlayerSettings, SourceHealth, SourceObservation
from .normalize import normalize_field
from .reconcile import reconcile
from .report import render_report
from .sources import get_source
from .sources.base import AccessPolicy, ParsedPlayer, SourceError

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG = ROOT / "config"
WORK = ROOT / "work"
DATA_AGG = ROOT / "data" / "aggregate"
FIGURES_LATEST = ROOT / "figures" / "latest"
FIXTURES = ROOT / "tests" / "fixtures"


# ---------------------------------------------------------------------------
# config loading
# ---------------------------------------------------------------------------

def load_sources_config() -> dict:
    with open(CONFIG / "sources.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_cohort_config() -> dict:
    with open(CONFIG / "cohort.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def enabled_sources(scheduled_only: bool) -> list[tuple[str, dict]]:
    cfg = load_sources_config()
    out = []
    for name, sc in (cfg.get("sources") or {}).items():
        if not sc.get("enabled", False):
            continue
        if scheduled_only and not sc.get("enabled_for_schedule", False):
            continue
        out.append((name, sc))
    return out


# ---------------------------------------------------------------------------
# fixture adapter (offline mode)
# ---------------------------------------------------------------------------

class _FixtureSource:
    """Reads minimized HTML fixtures instead of the network."""

    name = "cs2settings"

    def __init__(self, fixture_dir: Path) -> None:
        from .sources.cs2settings import CS2SettingsSource

        self._real = CS2SettingsSource()
        self.fixture_dir = fixture_dir

    def list_players(self) -> list[dict]:
        return [
            {"source_id": p.stem, "name": p.stem, "team": "Fixture"}
            for p in sorted(self.fixture_dir.glob("*.html"))
        ]

    def fetch_player(self, source_id: str) -> ParsedPlayer:
        path = self.fixture_dir / f"{source_id}.html"
        if not path.exists():
            raise SourceError(f"fixture missing: {path}")
        html = path.read_text(encoding="utf-8")
        # reuse the real parser via a temp override
        orig = self._real._get_text

        def fake_get(url: str) -> str:
            return html

        self._real._get_text = fake_get  # type: ignore[method-assign]
        try:
            from .sources.cs2settings import _extract_player_blob

            blob = _extract_player_blob(html)
            return self._real._blob_to_parsed(source_id, f"fixture://{source_id}", blob)
        finally:
            self._real._get_text = orig  # type: ignore[method-assign]

    def check_access_policy(self) -> AccessPolicy:
        return AccessPolicy(robots_allows=True, accessible=True, notes="offline fixture mode")


# ---------------------------------------------------------------------------
# pipeline steps
# ---------------------------------------------------------------------------

def _write_work(name: str, obj) -> Path:
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK / name
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def step_audit(scheduled_only: bool, offline: bool) -> dict:
    status: dict[str, str] = {}
    for name, _sc in enabled_sources(scheduled_only):
        src = _FixtureSource(FIXTURES / name) if offline else get_source(name)
        try:
            policy = src.check_access_policy()
            ok = policy.robots_allows and policy.accessible
            status[name] = "ok" if ok else f"blocked: {policy.notes}"
        except SourceError as exc:
            status[name] = f"error: {exc}"
    _write_work("source-status.json", status)
    return status


def cohort_scope() -> dict:
    """Build the scope block for metrics from config/cohort.yaml."""
    cfg = load_cohort_config()
    teams = sorted(cfg.get("teams") or [])
    return {
        "scope_id": cfg.get("scope_id", "unknown"),
        "tracked_teams": teams,
        "tracked_team_count": len(teams),
        "mode": cfg.get("mode", "tracked_teams"),
    }


def step_collect(
    scheduled_only: bool,
    offline: bool,
    source_filter: Optional[str],
    players: Optional[list[str]],
) -> list[SourceObservation]:
    observations: list[SourceObservation] = []
    identity = IdentityIndex()

    for name, _sc in enabled_sources(scheduled_only):
        if source_filter and name != source_filter:
            continue
        if offline and name != "cs2settings":
            continue  # fixtures only exist for the primary source
        src = _FixtureSource(FIXTURES / name) if offline else get_source(name)
        try:
            if players:
                roster = [{"source_id": p} for p in players]
            elif offline:
                roster = src.list_players()
            else:
                # cohort mode: tracked-team rosters from the primary source
                cohort = load_cohort_config()
                roster_fn = getattr(src, "list_team_roster", None)
                if cohort.get("mode") == "tracked_teams" and roster_fn is not None:
                    roster = []
                    seen: set[str] = set()
                    for slug in cohort.get("teams") or []:
                        try:
                            for entry in roster_fn(slug):
                                if entry["source_id"] not in seen:
                                    seen.add(entry["source_id"])
                                    roster.append(entry)
                        except SourceError as exc:
                            print(f"  [!] {name}/teams/{slug}: {exc}")
                else:
                    roster = src.list_players()
        except SourceError as exc:
            raise SystemExit(f"collect: {name} roster failed: {exc}") from exc

        for entry in roster:
            source_id = entry["source_id"]
            try:
                parsed = src.fetch_player(source_id)
            except SourceError as exc:
                print(f"  [!] {name}/{source_id}: {exc}")
                continue
            ident = identity.register(
                source=name,
                source_id=source_id,
                name=parsed.name,
                team=parsed.team,
                steam_id=parsed.steam_id,
                country=parsed.country,
                role=parsed.role,
            )
            for raw_field, raw_value in parsed.fields.items():
                attr, value = normalize_field(raw_field, raw_value)
                if attr is None:
                    continue
                observations.append(
                    SourceObservation(
                        player_id=ident.player_id,
                        field=attr,
                        value=value,
                        source=name,
                        source_url=parsed.source_url,
                        retrieved_at=parsed.retrieved_at,
                        source_updated_at=parsed.source_updated_at,
                        raw_label=str(raw_value),
                    )
                )

    _write_work("observations.json", [obs.__dict__ for obs in observations])
    _write_work("identities.json", {
        "players": [p.__dict__ for p in identity.all()],
        "problems": identity.identity_problems,
    })
    return observations


def step_normalize(observations: list[SourceObservation]) -> None:
    _write_work("normalized-observations.json", [obs.__dict__ for obs in observations])


def step_reconcile(observations: list[SourceObservation]) -> tuple[dict, list[dict]]:
    cfg = load_sources_config()
    enabled = {name for name, _sc in enabled_sources(False)}
    result = reconcile(observations, cfg.get("field_priority", {}), enabled)
    players = {pid: s.as_dict() for pid, s in result.players.items()}
    _write_work("current-normalized.json", players)
    _write_work("conflicts.json", result.conflicts)
    return players, result.conflicts


def step_metrics(players: dict) -> dict:
    objs = [NormalizedPlayerSettings.from_dict(d) for d in players.values()]
    metrics = compute_metrics(objs, snapshot_date=date.today().isoformat(),
                              source_note="v2-pipeline", scope=cohort_scope())
    _write_work("metrics.json", metrics)
    return metrics


def step_drift(baseline_path: Path) -> DriftReport:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    metrics = json.loads((WORK / "metrics.json").read_text(encoding="utf-8"))
    report = compute_drift(baseline, metrics, conclusions=load_conclusions(str(CONFIG / "conclusions.yaml")))
    _write_work("drift.json", {
        "level": report.level,
        "changed_metrics": report.changed_metrics,
        "cohort_change": report.cohort_change,
        "matched_panel_change": report.matched_panel_change,
        "baseline_snapshot_date": report.baseline_snapshot_date,
        "current_snapshot_date": report.current_snapshot_date,
        "scope_changed": report.scope_changed,
        "scope_warning": report.scope_warning,
    })
    return report


def step_report(candidate: bool) -> Path:
    metrics = json.loads((WORK / "metrics.json").read_text(encoding="utf-8"))
    conflicts = json.loads((WORK / "conflicts.json").read_text(encoding="utf-8"))
    drift = json.loads((WORK / "drift.json").read_text(encoding="utf-8"))
    status = json.loads((WORK / "source-status.json").read_text(encoding="utf-8"))
    baseline = None
    bp = DATA_AGG / "latest.json"
    if bp.exists():
        baseline = json.loads(bp.read_text(encoding="utf-8"))

    text = render_report(
        metrics=metrics,
        drift=drift,
        source_status=status,
        conflicts=conflicts,
        baseline=baseline,
    )
    if candidate:
        out = WORK / "report-candidate.md"
    else:
        out = ROOT / "reports" / "latest.md"
    out.write_text(text, encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def cmd_audit(args) -> int:
    status = step_audit(args.scheduled, args.offline)
    for name, st in status.items():
        print(f"{name}: {st}")
    return 0


def cmd_collect(args) -> int:
    players = args.players.split(",") if args.players else None
    obs = step_collect(args.scheduled, args.offline, args.source, players)
    print(f"collected {len(obs)} observations")
    return 0


def cmd_normalize(args) -> int:
    obs = [SourceObservation(**d) for d in json.loads((WORK / "observations.json").read_text(encoding="utf-8"))]
    step_normalize(obs)
    print(f"normalized {len(obs)} observations")
    return 0


def cmd_reconcile(args) -> int:
    obs = [SourceObservation(**d) for d in json.loads((WORK / "observations.json").read_text(encoding="utf-8"))]
    players, conflicts = step_reconcile(obs)
    print(f"reconciled {len(players)} players; {len(conflicts)} conflicts")
    return 0


def cmd_metrics(args) -> int:
    players = json.loads((WORK / "current-normalized.json").read_text(encoding="utf-8"))
    metrics = step_metrics(players)
    agg = public_aggregate(metrics)["aggregate"]
    print(f"players={agg['player_count']} teams={agg['team_count']}")
    return 0


def cmd_drift(args) -> int:
    report = step_drift(args.baseline)
    print(f"drift level: {report.level}")
    for c in report.changed_metrics:
        print(f"  [{c['level']}] {c['conclusion']}: {c['baseline']} -> {c['current']}")
    return 0


def cmd_report(args) -> int:
    out = step_report(candidate=args.candidate)
    print(f"report written: {out}")
    return 0


def cmd_update(args) -> int:
    status = step_audit(args.scheduled, args.offline)
    failed = [n for n, s in status.items() if not s.startswith("ok")]
    if failed:
        print(f"source audit failed for: {failed}")
        print("no collection attempted (fail closed)")
        return 1
    players = args.players.split(",") if args.players else None
    obs = step_collect(args.scheduled, args.offline, args.source, players)
    if not obs:
        print("no observations collected")
        return 1
    step_normalize(obs)
    reconciled, conflicts = step_reconcile(obs)
    step_metrics(reconciled)
    report = step_drift(args.baseline)
    out = step_report(candidate=True)
    print(f"observations={len(obs)} players={len(reconciled)} conflicts={len(conflicts)}")
    print(f"drift level: {report.level}")
    print(f"candidate report: {out}")
    return 0


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="cs2-pro-settings")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("audit-sources", "collect", "normalize", "reconcile", "metrics", "drift", "report", "update"):
        p = sub.add_parser(name)
        p.add_argument("--offline", action="store_true", help="use test fixtures")
        p.add_argument("--scheduled", action="store_true", help="enabled_for_schedule sources only")
        p.add_argument("--source", default=None, help="restrict to one source")
        p.add_argument("--players", default=None, help="comma-separated player ids")
        p.add_argument("--candidate", action="store_true", help="report -> work/report-candidate.md")
        p.add_argument("--baseline", default=str(DATA_AGG / "latest.json"), help="baseline aggregate JSON")

    args = parser.parse_args(argv)
    dispatch = {
        "audit-sources": cmd_audit,
        "collect": cmd_collect,
        "normalize": cmd_normalize,
        "metrics": cmd_metrics,
        "drift": cmd_drift,
        "report": cmd_report,
        "update": cmd_update,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
