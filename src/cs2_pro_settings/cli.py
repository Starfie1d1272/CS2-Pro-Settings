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
    """Build the scope block for metrics from config/cohort.yaml (v3)."""
    from .cohort import core_slugs, tracked_slugs

    cfg = load_cohort_config()
    universe = tracked_slugs(cfg)
    core = core_slugs(cfg)
    core_cfg = cfg.get("cohort", {}).get("core", {})
    return {
        "scope_id": "top-tier-plus-selected-v1",  # legacy-compatible id
        "cohort_model": "core-watchlist-supplemental-v3",
        "core_snapshot": core_cfg.get("snapshot"),
        "tracked_teams": universe,
        "tracked_team_count": len(universe),
        "core_team_count": len(core),
        "mode": cfg.get("mode", "tracked_teams"),
    }


def step_collect(
    scheduled_only: bool,
    offline: bool,
    source_filter: Optional[str],
    players: Optional[list[str]],
) -> tuple[list[SourceObservation], dict[str, list[str]]]:
    observations: list[SourceObservation] = []
    roster_by_team: dict[str, list[str]] = {}
    identity = IdentityIndex()
    cohort_cfg = load_cohort_config()

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
                # cohort v3: tracked universe = Core ∪ Watchlist ∪ Supplemental
                from .cohort import tracked_slugs

                roster_fn = getattr(src, "list_team_roster", None)
                if roster_fn is not None:
                    roster = []
                    seen: set[str] = set()
                    for slug in tracked_slugs(cohort_cfg):
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
            # cohort policy: role filter (coach/retired/content_creator excluded)
            from .cohort import player_allowed

            allowed, reason = player_allowed(parsed.role, cohort_cfg)
            if not allowed:
                print(f"  [-] {name}/{source_id}: {reason} (excluded)")
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
            # roster snapshot: stable player_id per team (slug from source)
            if parsed.team:
                roster_by_team.setdefault(parsed.team, [])
                if ident.player_id not in roster_by_team[parsed.team]:
                    roster_by_team[parsed.team].append(ident.player_id)
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
    return observations, roster_by_team


def step_normalize(observations: list[SourceObservation]) -> None:
    _write_work("normalized-observations.json", [obs.__dict__ for obs in observations])


def step_reconcile(observations: list[SourceObservation]) -> tuple[dict, list[dict]]:
    from .cohort import resolve_team_tier
    from .models import PlayerIdentity

    cfg = load_sources_config()
    enabled = {name for name, _sc in enabled_sources(False)}
    identities: dict[str, PlayerIdentity] = {}
    id_path = WORK / "identities.json"
    if id_path.exists():
        id_data = json.loads(id_path.read_text(encoding="utf-8"))
        for d in id_data.get("players") or []:
            identities[d["player_id"]] = PlayerIdentity(**d)
    result = reconcile(observations, cfg.get("field_priority", {}), enabled, identities)
    cohort_cfg = load_cohort_config()
    for s in result.players.values():
        s.cohort_tier = resolve_team_tier(s.team, cohort_cfg)
    players = {pid: s.as_dict() for pid, s in result.players.items()}
    _write_work("current-normalized.json", players)
    _write_work("conflicts.json", result.conflicts)
    return players, result.conflicts


def step_metrics(players: dict) -> dict:
    objs = [NormalizedPlayerSettings.from_dict(d) for d in players.values()]
    today = date.today().isoformat()
    scope = cohort_scope()

    def seg(tiers):
        return [p for p in objs if p.cohort_tier in tiers]

    core_players = seg({"core"})
    core_watch_players = seg({"core", "watchlist"})

    core_agg = compute_metrics(
        core_players, today, source_note="v2-core", scope=scope,
        series={"series_id": "hltv-core-v2", "cohort_semantics": "core_top30"})["aggregate"]
    metrics = {
        "aggregate": core_agg,
        "segments": {
            "core": core_agg,
            "core_plus_watchlist": compute_metrics(
                core_watch_players, today, source_note="v2-core+watchlist", scope=scope,
                series={"series_id": "hltv-core-v2", "cohort_semantics": "core_plus_watchlist"})["aggregate"],
            "all_tracked": compute_metrics(
                objs, today, source_note="v2-all-tracked", scope=scope,
                series={"series_id": "hltv-core-v2", "cohort_semantics": "all_tracked"})["aggregate"],
        },
        "panel": {
            "status": "available" if core_players else "empty",
            "player_ids": sorted(p.player_id for p in core_players),
            "players": {
                p.player_id: {
                    "dpi": p.dpi,
                    "edpi": p.edpi,
                    "resolution": p.resolution,
                    "polling_rate": p.polling_rate,
                }
                for p in core_players
            },
        },
    }
    _write_work("metrics.json", metrics)
    return metrics


def step_drift(baseline_path: Path) -> DriftReport:
    baseline_path = Path(baseline_path)
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    metrics = json.loads((WORK / "metrics.json").read_text(encoding="utf-8"))
    # roster info from this run (work/roster-report.json)
    turnover = None
    rp = WORK / "roster-report.json"
    if rp.exists():
        rr = json.loads(rp.read_text(encoding="utf-8"))
        turnover = rr.get("turnover_rate")
    # previous matched panel from cross-run runtime state (not work/)
    from . import runtime_state

    prev_panel = runtime_state.load_previous_panel_for_drift()
    with open(CONFIG / "stability.yaml", encoding="utf-8") as f:
        stability_cfg = yaml.safe_load(f) or {}
    threshold = (stability_cfg.get("roster") or {}).get("turnover_threshold", 0.15)
    report = compute_drift(
        baseline,
        metrics,
        conclusions=load_conclusions(str(CONFIG / "conclusions.yaml")),
        previous_panel=prev_panel,
        roster_turnover_rate=turnover,
        turnover_threshold=threshold,
    )
    _write_work("drift.json", {
        "level": report.level,
        "changed_metrics": report.changed_metrics,
        "cohort_change": report.cohort_change,
        "matched_panel_change": report.matched_panel_change,
        "baseline_snapshot_date": report.baseline_snapshot_date,
        "current_snapshot_date": report.current_snapshot_date,
        "scope_changed": report.scope_changed,
        "scope_warning": report.scope_warning,
        "cohort_stability": report.cohort_stability,
        "roster_turnover_rate": report.roster_turnover_rate,
        "headline_suppressed": report.headline_suppressed,
        "suppression_reason": report.suppression_reason,
        "series_compatible": report.series_compatible,
        "baseline_incompatible_reason": report.baseline_incompatible_reason,
    })
    return report


def step_report(candidate: bool) -> Path:
    metrics = json.loads((WORK / "metrics.json").read_text(encoding="utf-8"))
    conflicts = json.loads((WORK / "conflicts.json").read_text(encoding="utf-8"))
    drift = json.loads((WORK / "drift.json").read_text(encoding="utf-8"))
    status = json.loads((WORK / "source-status.json").read_text(encoding="utf-8"))
    roster_report = None
    rr_path = WORK / "roster-report.json"
    if rr_path.exists():
        roster_report = json.loads(rr_path.read_text(encoding="utf-8"))
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
        roster_report=roster_report,
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
    obs, roster = step_collect(args.scheduled, args.offline, args.source, players)
    print(f"collected {len(obs)} observations; {len(roster)} teams in roster")
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


def step_roster(roster_by_team: dict[str, list[str]], observed_at: str) -> dict:
    """Compare current roster vs persisted previous state (cross-run).

    State lives in .runtime-state/ (GitHub Actions cache, gitignored):
      roster-previous.json — last SUCCESSFUL production run's roster
      roster-pending.json  — confirmation window state

    Warm-up semantics: if no previous state exists (cache miss / first run),
    we do NOT treat every player as "added": status=warmup, turnover
    unavailable, no roster-change signal. State is advanced only after the
    whole pipeline succeeds (cmd_update).
    """
    from . import runtime_state
    from .roster import compute_roster_report, update_pending_state

    previous = runtime_state.load_state("roster-previous.json")
    pending = runtime_state.load_state("roster-pending.json")
    current = {k: sorted(v) for k, v in roster_by_team.items()}

    if previous is None:
        # warm-up run: initialize, do not diff against an empty universe
        report_dict = {
            "observed_at": observed_at,
            "previous_total": None,
            "current_total": sum(len(v) for v in current.values()),
            "matched_total": None,
            "turnover_rate": None,
            "has_changes": False,
            "has_comparable_previous": False,
            "fingerprint": None,
            "team_drifts": [],
            "pending_state": None,
            "status": "warmup",
        }
        _write_work("roster-report.json", report_dict)
        return {"turnover_rate": None, "has_changes": False,
                "pending_state": None, "status": "warmup",
                "has_comparable_previous": False}

    report = compute_roster_report(observed_at, previous, current)
    new_pending = update_pending_state(pending, report, observed_at)
    _write_work("roster-report.json", {
        "observed_at": report.observed_at,
        "previous_total": report.previous_total,
        "current_total": report.current_total,
        "matched_total": report.matched_total,
        "turnover_rate": report.turnover_rate,
        "has_changes": report.has_changes,
        "has_comparable_previous": True,
        "fingerprint": report.fingerprint(),
        "team_drifts": [d.__dict__ for d in report.team_drifts],
        "pending_state": new_pending,
        "status": "compared",
    })
    return {
        "turnover_rate": report.turnover_rate,
        "has_changes": report.has_changes,
        "pending_state": new_pending,
        "status": "compared",
        "has_comparable_previous": True,
    }


def _persist_runtime_state(roster_by_team: dict[str, list[str]], metrics: dict,
                           roster_pending: Optional[dict]) -> None:
    """Advance runtime state ONLY on a fully successful pipeline run.

    The roster baseline advances only when the change is CONFIRMED (or when
    there is no pending change). While a change is pending, the confirmed
    baseline is kept so the next run can confirm the same fingerprint.
    """
    from . import runtime_state

    if roster_pending is None or roster_pending.get("status") == "confirmed":
        current = {k: sorted(v) for k, v in roster_by_team.items()}
        runtime_state.save_state("roster-previous.json", current)
        runtime_state.clear_state("roster-pending.json")
    else:
        # change still pending: keep baseline, persist the confirmation window
        runtime_state.save_state("roster-pending.json", roster_pending)
    prev_panel = runtime_state.build_previous_panel(metrics)
    runtime_state.save_state("previous-panel.json", prev_panel)
    runtime_state.save_state("state-meta.json", {
        "last_successful_run": date.today().isoformat(),
        "warmup": False,
    })


def cmd_update(args) -> int:
    from . import runtime_state

    status = step_audit(args.scheduled, args.offline)
    failed = [n for n, s in status.items() if not s.startswith("ok")]
    if failed:
        print(f"source audit failed for: {failed}")
        print("no collection attempted (fail closed)")
        return 1
    players = args.players.split(",") if args.players else None
    obs, roster = step_collect(args.scheduled, args.offline, args.source, players)
    if not obs:
        print("no observations collected")
        return 1
    roster_info = step_roster(roster, date.today().isoformat())
    print(f"roster: status={roster_info.get('status')} "
          f"turnover={roster_info['turnover_rate']} "
          f"changes={roster_info['has_changes']} pending={roster_info['pending_state']}")
    step_normalize(obs)
    reconciled, conflicts = step_reconcile(obs)
    metrics = step_metrics(reconciled)
    report = step_drift(args.baseline)
    out = step_report(candidate=True)
    # pipeline succeeded: advance cross-run runtime state
    _persist_runtime_state(roster, metrics, roster_info.get("pending_state"))
    print(f"observations={len(obs)} players={len(reconciled)} conflicts={len(conflicts)}")
    print(f"drift level: {report.level}")
    print(f"candidate report: {out}")
    return 0


# ---------------------------------------------------------------------------
# ranking commands (manual HLTV snapshots)
# ---------------------------------------------------------------------------

def cmd_ranking_import(args) -> int:
    from .rankings import (
        RankingError,
        build_snapshot,
        load_mappings,
        parse_top30,
        ranking_diff,
        save_snapshot,
    )

    try:
        if args.stdin:
            text = sys.stdin.read()
        elif args.file:
            text = Path(args.file).read_text(encoding="utf-8")
        else:
            print("error: provide --stdin or --file")
            return 2
        entries = parse_top30(text)
        mappings = load_mappings() if not args.no_mapping else None
        snapshot = build_snapshot(
            entries, args.source_url, args.date, mappings=mappings,
            allow_unresolved=args.allow_unresolved,
        )
        # diff vs previously accepted ranking (if any)
        out = save_snapshot(snapshot, args.rankings_dir)
        print(f"validated: {len(entries)} teams (ranks 1-30, unique, continuous)")
        print(f"written: {out}")
        prev_snap = args.previous
        if prev_snap and Path(prev_snap).exists():
            import yaml as _yaml

            prev = _yaml.safe_load(Path(prev_snap).read_text(encoding="utf-8")) or {}
            diff = ranking_diff(prev, snapshot)
            print("ENTERED CORE:", diff["entered_core"] or "(none)")
            print("EXITED CORE:", diff["exited_core"] or "(none)")
            print("RANK MOVEMENTS:", diff["rank_movements"] or "(none)")
            for s in diff["review_suggestions"]:
                print(f"  suggestion: {s['team_id']} -> {s['suggestion']}")
        print("NOTE: snapshot is a candidate; activate by updating config/cohort.yaml "
              "(cohort.core) after review (see config/rankings/hltv/README.md).")
        return 0
    except (RankingError, ValueError) as exc:
        print(f"RANKING ERROR: {exc}")
        return 1


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

    rank = sub.add_parser("ranking")
    rsub = rank.add_subparsers(dest="ranking_command", required=True)
    imp = rsub.add_parser("import-hltv")
    imp.add_argument("--date", required=True, help="ranking snapshot date YYYY-MM-DD")
    imp.add_argument("--source-url", required=True, help="HLTV ranking page URL")
    imp.add_argument("--stdin", action="store_true", help="read Top 30 from stdin")
    imp.add_argument("--file", default=None, help="read Top 30 from file")
    imp.add_argument("--allow-unresolved", action="store_true",
                     help="emit candidate with explicit unresolved status instead of failing")
    imp.add_argument("--no-mapping", action="store_true", help="skip team mapping (testing)")
    imp.add_argument("--rankings-dir", default="config/rankings/hltv")
    imp.add_argument("--previous", default=None, help="previous accepted snapshot path for diff")

    args = parser.parse_args(argv)
    if args.command == "ranking":
        return cmd_ranking_import(args)
    dispatch = {
        "audit-sources": cmd_audit,
        "collect": cmd_collect,
        "normalize": cmd_normalize,
        "reconcile": cmd_reconcile,
        "metrics": cmd_metrics,
        "drift": cmd_drift,
        "report": cmd_report,
        "update": cmd_update,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
