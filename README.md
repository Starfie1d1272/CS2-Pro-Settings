# CS2 Pro Settings Tracker

A reproducible longitudinal data pipeline for tracking how professional
Counter-Strike 2 settings evolve over time.

This project started as a one-off May 2026 analysis of 198 active pro
players. It is now a scheduled, multi-source, provenance-aware pipeline that
detects conclusion changes and raises notifications / candidate PRs —
without auto-merging and without LLM-generated interpretation.

## 1. What this project does

- Collects professional CS2 player settings from public sources (normal HTTP
  only; no anti-bot bypass).
- Resolves **stable player identities** (SteamID-based when available; never
  a bare nickname).
- Tracks the **tracked-team roster** over time (roster snapshots, turnover,
  offseason guard).
- Produces deterministic aggregate metrics where **every share carries its
  valid_n** (a missing field never defaults to the full cohort).
- Detects **conclusion drift** with deterministic Level 0/1/2 rules.
- Separates **current-cohort** analysis from **matched-panel** analysis
  (same players across snapshots).
- Runs scheduled monitoring (daily / weekly) via GitHub Actions; issues and
  candidate PRs are deduplicated; nothing is auto-merged.

## 2. Current accepted snapshot

| | |
|---|---|
| snapshot date | **2026-05-05** (historical accepted baseline) |
| scope | 41 teams / 198 players |
| artifacts | `data/aggregate/2026-05.json`, `reports/2026-05.md` |

The v2 monitoring pipeline was added in 2026-08. It has not yet produced an
accepted live snapshot; until a full candidate snapshot is reviewed and
merged, the accepted baseline remains 2026-05-05. Do not treat offline
fixture runs or partial live smoke tests as snapshots.

## 3. v2 architecture

```
sources (adapters, fail closed)
  -> identity (steam:<id> canonical)
  -> roster snapshots (team -> stable player ids)
  -> normalize (all parsing rules in one place)
  -> reconcile (conflicts surfaced, never silently overwritten)
  -> metrics (deterministic aggregate + panel)
  -> drift (Level 0/1/2, suppression rules)
  -> report (deterministic markdown, no LLM)
```

Code lives in `src/cs2_pro_settings/`; run it with
`python -m cs2_pro_settings <command>` (see section 8).

## 4. Automatic monitoring

- **CI** (`.github/workflows/ci.yml`): pytest + offline fixture end-to-end +
  deterministic-output check on every PR/push. Never touches the network for
  sources.
- **Daily** (`.github/workflows/daily-update.yml`, 08:17 Asia/Shanghai):
  source health → scope → roster → settings → metrics → drift. Actions:
  - Level 0: nothing.
  - Level 1: deduplicated `[data-drift]` issue.
  - Level 2 (scope stable AND roster stable): candidate PR
    `automation/settings-update-YYYYMMDD` (deduplicated — at most one open
    candidate PR per drift).
  - Confirmed roster change: deduplicated `[roster-change]` issue.
  - Primary source unhealthy: deduplicated `[data-source]` issue; baseline
    not updated.
- **Weekly** (`.github/workflows/weekly-reconcile.yml`, Sunday 08:47
  Asia/Shanghai): source health, scope, roster, identity problems,
  missingness, conflict rate, monthly-snapshot due check; deduplicated
  `[data-quality]` issue.
- **Monthly**: when the current month's `data/aggregate/YYYY-MM.json` is
  missing, a monthly aggregate snapshot candidate is created even without a
  Level 2 change (merged into the existing automation PR if one is open).

Every workflow uses the repository `GITHUB_TOKEN`; no PATs. Dry runs are the
default for `workflow_dispatch` (`dry_run=true`): live fetch allowed, no
issues/commits/PRs.

## 5. Cohort and roster changes

### Cohort model v4: VRS Core + HLTV reference + ranked universe + Watchlist

- **Core (primary)** — accepted **Valve Global Ranking (VRS) Top 30**
  snapshot (`config/rankings/valve/2026-08-10.yaml`). VRS is the chosen
  PRIMARY competitive scope for this project — a project methodology
  decision, not a claim that any other ranking is useless.
- **Reference** — accepted **HLTV World Ranking Top 30** snapshot
  (`config/rankings/hltv/2026-08-03.yaml`), a sensitivity/reference panel.
- **Consensus** = VRS ∩ HLTV (27 teams, first round) — robustness panel.
- **Ranked union** = VRS ∪ HLTV (33 teams, first round) — scheduled
  tracking universe.
- **Watchlist** — manual observation choices (BC.Game, 100 Thieves, M80,
  Lynn Vision). They imply nothing about current VRS/HLTV membership;
  BC.Game has no resolvable settings page and stays `coverage=unresolved`
  rather than fabricated.

Headline statistics use **Core only**; `consensus`, `ranked_union`,
`core_plus_watchlist` and `all_tracked` are reported as separate segments.

**Ranking truth and source coverage are independent** (hard invariant):
an unresolved settings source mapping lowers collection coverage only — it
never invalidates a ranking. Ranking rosters (player names on ranking
pages) are never imported and never treated as current roster truth.

### Manual HLTV/VRS rankings (no scraping)

HLTV ranking is **not scraped** (anti-bot / access limitation; bypassing is
out of scope by policy). Ranking snapshots are:

- manually imported via `python -m cs2_pro_settings ranking import-hltv`
  (validates ranks 1–30, no duplicates, continuous numbering, source URL,
  and team mapping — unresolved teams fail or emit an explicit unresolved
  candidate that cannot be activated),
- versioned under `config/rankings/hltv/`,
- community-contributable (CONTRIBUTING.md, `docs/ranking-updates.md`,
  ranking-update issue template),
- intentionally low-maintenance: a stale ranking never blocks the settings
  pipeline; the report always names the accepted ranking date; only ≥180
  days triggers a deduplicated `[maintenance]` issue (30/90-day bands are
  status-only).

### Roster drift, matched panel, stability guard

- **Roster drift**: per-team added/removed/unchanged player diffs between
  runs, computed on stable player IDs. A change must be observed twice with
  the same fingerprint before it is **confirmed** (`.runtime-state/`, the
  Actions cache — gitignored) and notified; transient site desyncs do not
  cause noise.
- **Turnover**: `1 - matched / previous` players (Core players only for the
  headline guard; all-tracked turnover is recorded separately).
- **Stability guard (15%)**: `config/stability.yaml`
  (`roster.turnover_threshold: 0.15`) — an **operational automation
  threshold, not a statistical significance threshold**. When Core turnover
  ≥ 15% (or the Core scope changed), overall cohort metrics are still
  computed and may still notify at Level 1, but an overall
  dominant-category flip alone must NOT auto-produce a Level 2 headline PR
  (`headline_suppressed=true`).
- **Matched panel**: always computed independently when stable identities
  exist; a same-player material change is reported separately
  (matched-panel driven PRs are labeled as such).
- **Why this matters**: offseason roster changes can distort aggregate
  settings trends without any player actually changing their settings. The
  matched panel separates "settings evolution" from "roster composition
  change".

### Decision order

source health → ranking/core scope → roster → settings:

- source unhealthy: no baseline/state update, `[data-source]` issue;
- Core scope changed: overall Core headline Level 2 suppressed pending review;
- Core scope stable but roster turnover ≥15%: overall headline Level 2
  suppressed;
- Core scope stable and roster stable: normal Level 0/1/2;
- Watchlist/Supplemental changes alone can never trigger Core headline Level 2.

### Series compatibility

- `legacy-top30-plus-selected-v1` (2026-05-05, 41 teams / 198 players) is a
  legacy **extended** cohort — it is **not** a strict HLTV Top 30-only
  baseline, and its historical numbers are preserved unchanged.
- The v2 Core series is `vrs-core-v2`. Different series are **not directly
  comparable** for automated headline Level 1/2 (`series_compatible=false`);
  the first accepted vrs-core-v2 snapshot initializes the new longitudinal
  series.
- `RankingBasedScopeProvider` (auto-selecting a current ranking) remains a
  **planned extension only**; no ranking website is a live dependency until
  it has its own source/policy audit and explicit opt-in.

## 6. Multi-source model and provenance

"Multi-source" means the pipeline is multi-source at **independent layers**
— ranking scope, roster discovery, player identity, player settings and
source policy are separate concerns:

- **Ranking scope** — VRS Core (primary) + HLTV reference, manual
  snapshots, never scraped; ranking truth is `rank / team_id` + provenance
  and never carries source locators.
- **Roster discovery** — only sources with `roster_discovery: true` can
  list a team's current active roster. A missing team page in one source is
  a *roster discovery gap in that source*, never "the team has no data".
- **Player identity** — SteamID-safe merging only; nicknames are lookup
  hints, never identity. Identity crosswalks stay in runtime state.
- **Player settings** — reconciled by `field_priority` after identity-safe
  alignment; conflicts are surfaced, never silently overwritten.
- **Source policy** — `enabled` vs `enabled_for_schedule` vs
  local-review-only are separate; capability never grants permission.

| Source | Roster discovery | Player settings | Stable identity | Scheduled | Local review |
|---|---|---|---|---|---|
| cs2settings.com | yes | yes | yes | yes | yes |
| prosettings.net | no | yes | yes (numeric /profiles/) | **no** | yes |
| proconfig.net | no | yes | yes | no (disabled) | opt-in |

Per-source audits: `docs/source-audit/`. Adapters fail closed; no anti-bot
bypass, CAPTCHA solving, proxy rotation, or browser automation. Third-party
row-level data is **not** relicensed or redistributed in the current tree;
see `DATA_PROVENANCE.md`.

## 7. Conclusion drift

Deterministic rules in `config/conclusions.yaml` (no LLM):

- Level 1 (trend drift): share metrics move ≥ 5 percentage points
  (absolute); eDPI median moves ≥ 50.
- Level 2 (headline conclusion changed): the dominant category flips (e.g.
  800 DPI no longer dominant) or an explicit boolean conclusion flips.
- Suppression: if the tracked-team scope changed or roster turnover ≥ 15%,
  overall Level 2 is capped to Level 1 with `headline_suppressed=true`.

These thresholds are **operational notification thresholds, not
statistical significance**.

## 8. Reproduce locally

```bash
python -m venv .venv && source .venv/bin/activate   # or: conda env create -f environment.yml
pip install -e ".[dev]"

python -m cs2_pro_settings audit-sources            # source policy/access check
python -m cs2_pro_settings update --offline         # full pipeline on test fixtures (no network)
python -m cs2_pro_settings update --scheduled       # live pipeline, scheduled sources only
python -m pytest -v                                 # offline tests
```

Commands: `audit-sources`, `collect`, `normalize`, `reconcile`, `metrics`,
`drift`, `report`, `update` (chained: audit → collect → normalize →
reconcile → metrics → drift → report candidate), plus
`ranking import-vrs` / `ranking import-hltv` (manual Valve VRS / HLTV Top 30
import; HLTV is never scraped).

Runtime state is split: per-run artifacts go to `work/` (gitignored);
cross-run operational state (roster baseline, confirmation window, previous
matched panel) lives in `.runtime-state/` (gitignored) and is persisted
between production runs via the GitHub Actions cache. Cache loss causes a
safe warm-up run, never a false drift alert. Only `data/aggregate/`
snapshots are committed (and only on accepted updates / monthly snapshots).

## 9. Repository structure

```
src/cs2_pro_settings/       v2 canonical pipeline (models, identity, cohort,
                            normalize, reconcile, metrics, drift, roster,
                            rankings, runtime_state, scopes, report, plots,
                            cli, sources/)
config/                     cohort.yaml (Core/Watchlist/Supplemental),
                            sources.yaml, conclusions.yaml, stability.yaml,
                            team-mappings.yaml, cohort-2026-05-legacy.yaml,
                            rankings/hltv/ (manual snapshots)
data/aggregate/             accepted snapshot aggregates (2026-05.json, latest.json)
reports/                    2026-05.md (historical), latest.md (generated placeholder)
docs/source-audit/          per-source policy audits
docs/ranking-updates.md     how to contribute a ranking snapshot
notebooks/v1/               archived 2026-05 notebook pipeline (historical only)
tests/                      offline tests + fixtures (no live scraping in CI)
social/2026-05/             historical publication drafts
.github/workflows/          ci.yml, daily-update.yml, weekly-reconcile.yml
.github/ISSUE_TEMPLATE/     ranking-update.yml, watchlist.yml
scripts/                    actions_common.py, actions_daily.py, actions_weekly.py
```

## 10. Historical May 2026 analysis

`reports/2026-05.md` — the original deep-dive (41 teams / 198 players,
snapshot 2026-05-05) with the cyberpunk figures in `figures/`. It is a dated,
descriptive analysis of one snapshot; prevalence does not imply causal
performance benefit. Its figures are historical. `figures/latest/` is only
created when a vrs-core-v2 candidate snapshot is accepted — until then no
unaccepted candidate charts are published as "latest".

## 11. Licensing

- Source code: MIT (`LICENSE`).
- Reports, documentation, generated figures: CC BY 4.0 (`CONTENT_LICENSE.md`).
- Third-party source data: not relicensed by this repository
  (`DATA_PROVENANCE.md`). Old row-level source-derived data may remain in Git
  history because history was not rewritten; the current public tree no
  longer republishes it.

## 12. Limitations

- All statements describe the sampled tracked-team cohort; prevalence does
  not imply causal performance benefit.
- `valid_n` varies per field; a missing field never defaults to the full
  cohort size.
- Automated collection is limited to target paths that are accessible via
  ordinary HTTP and are not disallowed for the configured user agent by the
  source's robots policy; a robots allowance or absence of dedicated terms
  is NOT affirmative legal permission. No anti-bot bypass is used.
- Drift thresholds are operational, not statistical.
- Roster stability guards are designed for pro-circuit reality (offseason
  moves); they are intentionally conservative.
- Cross-run runtime state is best-effort operational state (GitHub Actions
  cache), not a database; a cache miss yields a safe warm-up run.
- Interpretive/conclusion text is written by humans; the pipeline produces
  deterministic data and reports only.
