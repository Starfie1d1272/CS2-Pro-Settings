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
from .report import read_legacy_metadata, render_report
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
    """Build the scope block for metrics from config/cohort.yaml (v4).

    Ranking defines competitive scope; the settings source defines
    observability. The scope block carries both: ranking membership truth
    (core/consensus/union by team_id) and source-resolved slugs.
    """
    from .cohort import _cs2_slug_of, load_cohort_sets, tracked_slugs

    cfg = load_cohort_config()
    sets = load_cohort_sets(cfg)
    universe = tracked_slugs(cfg)
    core_cfg = cfg.get("cohort", {}).get("core", {})
    ref_cfg = cfg.get("cohort", {}).get("reference", {})
    core_slugs_set = {s for s in (_cs2_slug_of(t) for t in (core_cfg.get("teams") or [])) if s}
    core_unresolved = sorted(
        t["team_id"] for t in (core_cfg.get("teams") or [])
        if not _cs2_slug_of(t))
    return {
        "scope_id": "vrs-core-v2",
        "cohort_model": "vrs-core-hltv-reference-v4",
        "core_snapshot": core_cfg.get("snapshot"),
        "core_provider": core_cfg.get("provider", "valve"),
        "reference_snapshot": ref_cfg.get("snapshot"),
        "reference_provider": ref_cfg.get("provider", "hltv"),
        "core_teams": sets["core_teams"],
        "reference_teams": sets["reference_teams"],
        "consensus_teams": sets["consensus_teams"],
        "ranked_union_teams": sets["ranked_union_teams"],
        "core_team_count": sets["core_count"],
        "reference_team_count": sets["reference_count"],
        "consensus_team_count": sets["consensus_count"],
        "ranked_union_team_count": sets["ranked_union_count"],
        "core_scope_hash": sets["core_scope_hash"],
        "tracked_teams": universe,
        "tracked_team_count": len(universe),
        "source_resolved_core_teams": len(core_slugs_set),
        "source_unresolved_core_teams": core_unresolved,
    }


def build_collection_manifest(
    requested_core_teams: int,
    source_resolved_core_teams: list[str],
    source_unresolved_core_teams: list[str],
    successful_core_team_rosters: list[str],
    failed_core_team_rosters: list[str],
    expected_core_players: int,
    successful_core_players: int,
    failed_core_players: list[str],
    all_tracked_requested: int,
    all_tracked_roster_failures: list[str],
    all_tracked_player_failures: list[str],
    reference_player_failures: list[str],
    watchlist_player_failures: list[str],
    mode: str = "scheduled",
    core_membership_ambiguities: Optional[list] = None,
) -> dict:
    """Deterministic collection manifest — fail closed on partial Core.

    Four INDEPENDENT layers (never conflated):
      1. ranking Core membership (requested_core_teams, e.g. 30)
      2. source resolution (which Core teams have a settings/roster page)
      3. roster collection (roster fetch success among resolved teams)
      4. player collection (settings fetch success among expected players)

    Expected players are determined from ROSTER LISTINGS (pre-fetch), never
    from fetch success. Each rate uses an explicit, named denominator.

    scheduled_collection_complete = the production gate: scheduled-policy
    sources only AND no Core roster-membership ambiguity.
    review_collection_complete = the local/manual gate: sources allowed for
    user-triggered review (may include local-only sources) AND no Core
    ambiguity. A review-complete state NEVER advances production state or
    publishes automation.
    """
    n_requested = requested_core_teams
    n_resolved = len(source_resolved_core_teams)
    n_unresolved = len(source_unresolved_core_teams)
    n_roster_ok = len(successful_core_team_rosters)
    n_roster_failed = len(failed_core_team_rosters)
    core_ambig = [a for a in (core_membership_ambiguities or []) if a.get("involves_core")]
    reasons: list[str] = []
    if n_requested <= 0:
        reasons.append("no requested core teams")
    if source_unresolved_core_teams:
        reasons.append(f"unresolved core source teams: {sorted(source_unresolved_core_teams)}")
    if failed_core_team_rosters:
        reasons.append(f"core roster fetch failures: {sorted(failed_core_team_rosters)}")
    if expected_core_players <= 0:
        reasons.append("no expected core players")
    if failed_core_players:
        reasons.append(f"core player settings failures: {sorted(failed_core_players)}")
    if successful_core_players != expected_core_players:
        reasons.append(f"core player collection mismatch: "
                       f"{successful_core_players} != expected {expected_core_players}")
    scheduled_complete = not reasons
    review_complete = not reasons  # review mode may add local-only sources later
    if core_ambig:
        ambig_reason = (f"core roster membership ambiguities: "
                        f"{[a['source_id'] for a in core_ambig]}")
        reasons.append(ambig_reason)
        scheduled_complete = False
        review_complete = False
    return {
        "mode": mode,
        "requested_core_teams": n_requested,
        "source_resolved_core_teams": n_resolved,
        "source_unresolved_core_teams": sorted(source_unresolved_core_teams),
        "successful_core_team_rosters": n_roster_ok,
        "failed_core_team_rosters": sorted(failed_core_team_rosters),
        "expected_core_players": expected_core_players,
        "successful_core_players": successful_core_players,
        "failed_core_players": sorted(failed_core_players),
        "core_source_resolution_rate": round(n_resolved / n_requested, 4) if n_requested else 0.0,
        "core_roster_coverage_rate": round(n_roster_ok / n_requested, 4) if n_requested else 0.0,
        "resolved_core_roster_success_rate": round(n_roster_ok / n_resolved, 4) if n_resolved else 0.0,
        "core_player_collection_rate": round(successful_core_players / expected_core_players, 4)
        if expected_core_players else 0.0,
        "collection_complete": scheduled_complete,  # legacy alias == scheduled gate
        "scheduled_collection_complete": scheduled_complete,
        "review_collection_complete": review_complete,
        "incomplete_reasons": reasons,
        "roster_membership_ambiguities": core_membership_ambiguities or [],
        "all_tracked_requested_teams": all_tracked_requested,
        "all_tracked_roster_failures": sorted(all_tracked_roster_failures),
        "all_tracked_player_failures": sorted(all_tracked_player_failures),
        "reference_player_failures": sorted(reference_player_failures),
        "watchlist_player_failures": sorted(watchlist_player_failures),
    }


def step_collect(
    scheduled_only: bool,
    offline: bool,
    source_filter: Optional[str],
    players: Optional[list[str]],
) -> tuple[list[SourceObservation], dict[str, list[str]], dict]:
    observations: list[SourceObservation] = []
    roster_by_team: dict[str, list[str]] = {}
    identity = IdentityIndex()
    cohort_cfg = load_cohort_config()
    from .cohort import player_allowed, tracked_slugs

    # ---- ranking Core membership (30) vs source resolution ----------------
    core_cfg = cohort_cfg.get("cohort", {}).get("core", {})
    core_source_slugs: list[str] = []
    core_unresolved_ids: list[str] = []
    if not (players or offline):
        from .cohort import _cs2_slug_of

        core_source_slugs = sorted(
            s for s in (_cs2_slug_of(t) for t in (core_cfg.get("teams") or [])) if s)
        core_unresolved_ids = sorted(
            t["team_id"] for t in (core_cfg.get("teams") or [])
            if not _cs2_slug_of(t))
    requested_core_teams = len(core_cfg.get("teams") or []) if not (players or offline) else 0
    core_roster_ok: list[str] = []
    core_roster_failures: list[str] = []
    core_expected: list[str] = []      # expected Core players from ROSTER listings
    core_success: list[str] = []       # successfully fetched Core players
    core_failures: list[str] = []
    all_tracked_requested: list[str] = []
    all_tracked_roster_failures: list[str] = []
    all_tracked_player_failures: list[str] = []
    reference_player_failures: list[str] = []
    watchlist_player_failures: list[str] = []
    team_membership_conflicts: list[dict] = []
    roster_membership_ambiguities: list[dict] = []

    # tier of each roster team slug: core / watchlist / reference / supplemental
    watch_slugs = set()
    for item in cohort_cfg.get("cohort", {}).get("watchlist") or []:
        if item.get("settings_slug"):
            watch_slugs.add(str(item["settings_slug"]))
    from .cohort import load_cohort_sets, team_ids_to_slugs

    _sets = load_cohort_sets(cohort_cfg)
    _slug_map = _sets.get("slug_map", {})
    core_slugs_set = set(core_source_slugs)
    hltv_only_slugs = set(team_ids_to_slugs(_sets["hltv_only_teams"], _slug_map))
    supp_slugs = set()
    for item in cohort_cfg.get("cohort", {}).get("supplemental") or []:
        if item.get("settings_slug"):
            supp_slugs.add(str(item["settings_slug"]))

    def _tier_of(slug: str) -> str:
        if slug in core_slugs_set:
            return "core"
        if slug in watch_slugs:
            return "watchlist"
        if slug in hltv_only_slugs:
            return "reference"
        if slug in supp_slugs:
            return "supplemental"
        return "other"

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
                # cohort v4: scheduled universe = ranked union ∪ watchlist;
                # team page origin defines CURRENT ROSTER MEMBERSHIP evidence.
                # All team pages are collected FIRST (source_id -> teams),
                # then membership ambiguity is resolved — never first-seen-wins.
                roster_fn = getattr(src, "list_team_roster", None)
                if roster_fn is not None:
                    entries_by_id: dict[str, list[dict]] = {}
                    for slug in tracked_slugs(cohort_cfg):
                        all_tracked_requested.append(slug)
                        try:
                            entries = roster_fn(slug)
                        except SourceError as exc:
                            print(f"  [!] {name}/teams/{slug}: {exc}")
                            all_tracked_roster_failures.append(slug)
                            if slug in core_slugs_set:
                                core_roster_failures.append(slug)
                            continue
                        if slug in core_slugs_set:
                            core_roster_ok.append(slug)
                        for entry in entries:
                            entry["roster_team_slug"] = slug
                            entry["cohort_membership"] = _tier_of(slug)
                            entries_by_id.setdefault(entry["source_id"], []).append(entry)
                    # membership resolution: a source_id on exactly ONE team
                    # page -> that team; on MULTIPLE team pages -> ambiguity
                    # (recorded; if it involves Core, scheduled fails closed).
                    # Nothing decides membership by crawl order or slug order.
                    roster = []
                    for sid, entries in entries_by_id.items():
                        teams = sorted({e["roster_team_slug"] for e in entries})
                        if len(teams) > 1:
                            involves_core = any(
                                e["cohort_membership"] == "core" for e in entries)
                            roster_membership_ambiguities.append({
                                "source_id": sid,
                                "teams": teams,
                                "involves_core": involves_core,
                            })
                            print(f"  [!] ambiguous roster membership {sid}: "
                                  f"{teams} (involves_core={involves_core})")
                            continue  # NOT assigned to any team
                        roster.append(entries[0])
                else:
                    roster = src.list_players()
        except SourceError as exc:
            raise SystemExit(f"collect: {name} roster failed: {exc}") from exc

        # ---- expected Core players BEFORE any fetch (roster listing) ------
        # roster page role is applied here so coaches never inflate expected
        for entry in roster:
            if entry.get("cohort_membership") != "core":
                continue
            allowed, _reason = player_allowed(entry.get("role"), cohort_cfg)
            if allowed and entry["source_id"] not in core_expected:
                core_expected.append(entry["source_id"])

        # ---- player fetch, classified by roster ORIGIN tier ----------------
        for entry in roster:
            source_id = entry["source_id"]
            roster_team = entry.get("roster_team_slug")
            tier = entry.get("cohort_membership", "other")
            try:
                parsed = src.fetch_player(source_id)
            except SourceError as exc:
                print(f"  [!] {name}/{source_id}: {exc}")
                if tier == "core":
                    core_failures.append(source_id)
                elif tier == "watchlist":
                    watchlist_player_failures.append(source_id)
                elif tier == "reference":
                    reference_player_failures.append(source_id)
                else:
                    all_tracked_player_failures.append(source_id)
                continue
            # cohort policy: role filter uses the SINGLE effective_role —
            # roster page role wins, player page role fills gaps; both
            # stages (expected & fetch) use the SAME inclusion criterion
            effective_role = entry.get("role") or parsed.role
            allowed, reason = player_allowed(effective_role, cohort_cfg)
            if not allowed:
                print(f"  [-] {name}/{source_id}: {reason} (excluded)")
                continue
            if tier == "core":
                core_success.append(source_id)
            # team membership: TEAM PAGE ORIGIN is the evidence; player page
            # teamId is a consistency check only (never silently override)
            membership_team = roster_team or parsed.team
            if (roster_team and parsed.team and parsed.team != roster_team):
                team_membership_conflicts.append({
                    "source_id": source_id,
                    "roster_team_slug": roster_team,
                    "player_page_team": parsed.team,
                    "source_url": parsed.source_url,
                })
            ident = identity.register(
                source=name,
                source_id=source_id,
                name=parsed.name,
                team=membership_team,
                steam_id=parsed.steam_id,
                country=parsed.country,
                role=effective_role,
            )
            # roster snapshot: stable player_id per team (roster ORIGIN team)
            if membership_team:
                roster_by_team.setdefault(membership_team, [])
                if ident.player_id not in roster_by_team[membership_team]:
                    roster_by_team[membership_team].append(ident.player_id)
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

    manifest = build_collection_manifest(
        requested_core_teams=requested_core_teams,
        source_resolved_core_teams=core_source_slugs,
        source_unresolved_core_teams=core_unresolved_ids,
        successful_core_team_rosters=core_roster_ok,
        failed_core_team_rosters=core_roster_failures,
        expected_core_players=len(core_expected),
        successful_core_players=len(core_success),
        failed_core_players=core_failures,
        all_tracked_requested=len(all_tracked_requested),
        all_tracked_roster_failures=all_tracked_roster_failures,
        all_tracked_player_failures=all_tracked_player_failures,
        reference_player_failures=reference_player_failures,
        watchlist_player_failures=watchlist_player_failures,
        mode="scheduled",
        core_membership_ambiguities=roster_membership_ambiguities,
    )
    _write_work("observations.json", [obs.__dict__ for obs in observations])
    _write_work("identities.json", {
        "players": [p.__dict__ for p in identity.all()],
        "problems": identity.identity_problems,
    })
    _write_work("collection-manifest.json", manifest)
    _write_work("team-membership-conflicts.json", team_membership_conflicts)
    _write_work("roster-membership-ambiguities.json", roster_membership_ambiguities)
    return observations, roster_by_team, manifest


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
    from .cohort import load_cohort_sets, team_ids_to_slugs, watchlist_slugs

    objs = [NormalizedPlayerSettings.from_dict(d) for d in players.values()]
    today = date.today().isoformat()
    scope = cohort_scope()
    cohort_cfg = load_cohort_config()
    sets = load_cohort_sets(cohort_cfg)
    slug_map = sets.get("slug_map", {})

    def seg(team_ids) -> list:
        slugs = set(team_ids_to_slugs(team_ids, slug_map))
        return [p for p in objs if p.team in slugs]

    core_players = seg(scope["core_teams"])
    core_slugs_set = {p.team for p in core_players}
    consensus_ids = scope["consensus_teams"]
    union_ids = scope["ranked_union_teams"]
    watch_slugs = set(watchlist_slugs(cohort_cfg))
    core_watch_players = [p for p in objs if p.team in core_slugs_set or p.team in watch_slugs]

    core_metrics = compute_metrics(
        core_players, today, source_note="v2-vrs-core", scope=scope,
        series={"series_id": "vrs-core-v2", "cohort_semantics": "core_top30"})
    core_agg = core_metrics["aggregate"]
    metrics = {
        "aggregate": core_agg,
        "figure_data": core_metrics["figure_data"],
        "segments": {
            "vrs_core": core_agg,
            "consensus": compute_metrics(
                seg(consensus_ids), today, source_note="v2-consensus", scope=scope,
                series={"series_id": "vrs-core-v2", "cohort_semantics": "consensus"})["aggregate"],
            "ranked_union": compute_metrics(
                seg(union_ids), today, source_note="v2-ranked-union", scope=scope,
                series={"series_id": "vrs-core-v2", "cohort_semantics": "ranked_union"})["aggregate"],
            "core_plus_watchlist": compute_metrics(
                core_watch_players, today, source_note="v2-core+watchlist", scope=scope,
                series={"series_id": "vrs-core-v2", "cohort_semantics": "core_plus_watchlist"})["aggregate"],
            "all_tracked": compute_metrics(
                objs, today, source_note="v2-all-tracked", scope=scope,
                series={"series_id": "vrs-core-v2", "cohort_semantics": "all_tracked"})["aggregate"],
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
    # roster info from this run (work/roster-report.json) — Core turnover
    # drives the headline guard; all-tracked turnover is monitoring only
    turnover = None
    rp = WORK / "roster-report.json"
    if rp.exists():
        rr = json.loads(rp.read_text(encoding="utf-8"))
        turnover = rr.get("core_turnover_rate", rr.get("turnover_rate"))
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
    manifest = None
    mf_path = WORK / "collection-manifest.json"
    if mf_path.exists():
        manifest = json.loads(mf_path.read_text(encoding="utf-8"))
    baseline = None
    bp = DATA_AGG / "latest.json"
    if bp.exists():
        baseline = json.loads(bp.read_text(encoding="utf-8"))
    cur_series = (metrics.get("aggregate", {}).get("series") or {}).get("series_id")
    legacy = read_legacy_metadata(DATA_AGG, cur_series)

    snapshot_date = (metrics.get("aggregate", {}) or {}).get("snapshot_date")
    month = (snapshot_date or date.today().isoformat())[:7]
    if len(month) != 7:
        month = date.today().strftime("%Y-%m")

    if candidate:
        out_en = WORK / "report-candidate.md"
        out_zh = WORK / "report-candidate.zh-CN.md"
        out_month_en = WORK / "report-candidate-monthly.md"
        out_month_zh = WORK / "report-candidate-monthly.zh-CN.md"
    else:
        out_en = ROOT / "reports" / "latest.md"
        out_zh = ROOT / "reports" / "latest.zh-CN.md"
        out_month_en = ROOT / "reports" / f"{month}.md"
        out_month_zh = ROOT / "reports" / f"{month}.zh-CN.md"

    common = dict(metrics=metrics, drift=drift, source_status=status,
                  conflicts=conflicts, baseline=baseline,
                  roster_report=roster_report, manifest=manifest,
                  legacy_snapshot=legacy)
    # latest pair: latest cross-links + mutable figures/latest scope
    out_en.write_text(render_report(locale="en", figure_scope="latest",
                                    cross_link_base="latest", **common),
                      encoding="utf-8")
    out_zh.write_text(render_report(locale="zh-CN", figure_scope="latest",
                                    cross_link_base="latest", **common),
                      encoding="utf-8")
    # monthly pair: same-month cross-links + immutable figures/YYYY-MM scope
    out_month_en.write_text(render_report(locale="en", figure_scope=month,
                                          cross_link_base=month, **common),
                            encoding="utf-8")
    out_month_zh.write_text(render_report(locale="zh-CN", figure_scope=month,
                                          cross_link_base=month, **common),
                            encoding="utf-8")
    return out_en


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
    obs, roster, manifest = step_collect(args.scheduled, args.offline, args.source, players)
    print(f"collected {len(obs)} observations; {len(roster)} teams in roster")
    print(f"manifest: collection_complete={manifest['collection_complete']} "
          f"core_teams={manifest['requested_core_teams']} "
          f"players={manifest['successful_core_players']}/{manifest['expected_core_players']}")
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

    # Core-only roster: headline stability uses ONLY VRS Core team memberships
    core_cfg = load_cohort_config().get("cohort", {}).get("core", {})
    from .cohort import _cs2_slug_of

    core_slugs_set = {s for s in (_cs2_slug_of(t) for t in (core_cfg.get("teams") or [])) if s}
    current_core = {k: v for k, v in current.items() if k in core_slugs_set}

    def _core_turnover(prev_all: Optional[dict]) -> Optional[float]:
        if prev_all is None:
            return None
        prev_core = {k: v for k, v in prev_all.items() if k in core_slugs_set}
        prev_ids = {pid for v in prev_core.values() for pid in v}
        cur_ids = {pid for v in current_core.values() for pid in v}
        matched = len(prev_ids & cur_ids)
        if not prev_ids:
            return None
        return round(1 - matched / len(prev_ids), 4)

    core_turnover = _core_turnover(previous)

    if previous is None:
        # warm-up run: initialize, do not diff against an empty universe
        report_dict = {
            "observed_at": observed_at,
            "previous_total": None,
            "current_total": sum(len(v) for v in current.values()),
            "matched_total": None,
            "turnover_rate": None,
            "core_turnover_rate": None,
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
                "has_comparable_previous": False, "core_turnover_rate": None}

    report = compute_roster_report(observed_at, previous, current)
    new_pending = update_pending_state(pending, report, observed_at)
    _write_work("roster-report.json", {
        "observed_at": report.observed_at,
        "previous_total": report.previous_total,
        "current_total": report.current_total,
        "matched_total": report.matched_total,
        "turnover_rate": report.turnover_rate,
        "core_turnover_rate": core_turnover,
        "has_changes": report.has_changes,
        "has_comparable_previous": True,
        "fingerprint": report.fingerprint(),
        "team_drifts": [d.__dict__ for d in report.team_drifts],
        "pending_state": new_pending,
        "status": "compared",
    })
    return {
        "turnover_rate": report.turnover_rate,
        "core_turnover_rate": core_turnover,
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
    status = step_audit(args.scheduled, args.offline)
    failed = [n for n, s in status.items() if not s.startswith("ok")]
    if failed:
        print(f"source audit failed for: {failed}")
        print("no collection attempted (fail closed)")
        return 1
    players = args.players.split(",") if args.players else None
    obs, roster, manifest = step_collect(args.scheduled, args.offline, args.source, players)
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
    print(f"observations={len(obs)} players={len(reconciled)} conflicts={len(conflicts)}")
    print(f"drift level: {report.level}")
    print(f"candidate report: {out}")
    if not manifest["collection_complete"]:
        print("COLLECTION INCOMPLETE: state NOT advanced; no publish/update allowed")
        print("incomplete reasons:", manifest["incomplete_reasons"])
        return 0
    # pipeline succeeded AND collection complete: advance cross-run state
    _persist_runtime_state(roster, metrics, roster_info.get("pending_state"))
    return 0


# ---------------------------------------------------------------------------
# ranking commands (manual VRS / HLTV snapshots)
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
            provider=args.provider, ranking_type=args.ranking_type,
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
    imp = rsub.add_parser("import-hltv", help="import a manual HLTV World Ranking Top 30")
    imp.add_argument("--date", required=True, help="ranking snapshot date YYYY-MM-DD")
    imp.add_argument("--source-url", required=True, help="HLTV ranking page URL")
    imp.add_argument("--stdin", action="store_true", help="read Top 30 from stdin")
    imp.add_argument("--file", default=None, help="read Top 30 from file")
    imp.add_argument("--allow-unresolved", action="store_true",
                     help="emit candidate with explicit unresolved status instead of failing")
    imp.add_argument("--no-mapping", action="store_true", help="skip team mapping (testing)")
    imp.add_argument("--rankings-dir", default="config/rankings/hltv")
    imp.add_argument("--previous", default=None, help="previous accepted snapshot path for diff")
    imp.set_defaults(provider="hltv", ranking_type="world")
    imp_v = rsub.add_parser("import-vrs", help="import a manual Valve Global Ranking (VRS) Top 30")
    imp_v.add_argument("--date", required=True, help="ranking snapshot date YYYY-MM-DD")
    imp_v.add_argument("--source-url", required=True, help="Valve ranking display page URL")
    imp_v.add_argument("--stdin", action="store_true", help="read Top 30 from stdin")
    imp_v.add_argument("--file", default=None, help="read Top 30 from file")
    imp_v.add_argument("--allow-unresolved", action="store_true",
                       help="emit candidate with explicit unresolved status instead of failing")
    imp_v.add_argument("--no-mapping", action="store_true", help="skip team mapping (testing)")
    imp_v.add_argument("--rankings-dir", default="config/rankings/valve")
    imp_v.add_argument("--previous", default=None, help="previous accepted snapshot path for diff")
    imp_v.set_defaults(provider="valve", ranking_type="global")

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
