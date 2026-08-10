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

- **Team scope**: the v2 cohort is the explicit, versioned tracked-team scope
  (`config/cohort.yaml`): `mode: tracked_teams`,
  `scope_id: top-tier-plus-selected-v1` — the same 41-team universe as the
  2026-05 snapshot, expressed as stable source team IDs (slugs). Roster
  membership is parsed from the primary source; there is **no 200+ nickname
  whitelist**.
- **Roster drift**: per-team added/removed/unchanged player diffs between
  runs, computed on stable player IDs. A change must be observed twice with
  the same fingerprint before it is **confirmed** (`work/roster-pending.json`
  — gitignored) and notified; transient site desyncs do not cause noise.
- **Turnover**: `1 - matched / previous` players.
- **Stability guard (15%)**: configured in `config/stability.yaml`
  (`roster.turnover_threshold: 0.15`). This is an **operational automation
  threshold, not a statistical significance threshold**. When turnover ≥ 15%
  (or the tracked-team scope changed), overall cohort metrics are still
  computed and may still notify at Level 1, but an overall dominant-category
  flip alone must NOT auto-produce a Level 2 headline PR
  (`headline_suppressed=true`).
- **Matched panel**: always computed independently when stable identities
  exist; a same-player material change is reported separately
  (matched-panel driven PRs are labeled as such).
- **Why this matters**: offseason roster changes can distort aggregate
  settings trends without any player actually changing their settings. The
  matched panel exists precisely to separate "settings evolution" from
  "roster composition change".
- **Dynamic ranking-based scope** (e.g. auto-selecting the current Top 30) is
  a **planned extension only**. No ranking website has been selected or
  audited; it will not become a live dependency until it has its own
  source/policy audit and explicit opt-in (`RankingBasedScopeProvider` is an
  interface stub).

## 6. Sources and provenance

| Source | Role | Schedule |
|---|---|---|
| cs2settings.com | primary (roster + settings) | enabled |
| prosettings.net | compatibility / local reconciliation | disabled for schedule |
| proconfig.net | secondary editorial cross-check | disabled (opt-in) |

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
reconcile → metrics → drift → report candidate).

Runtime state is written to `work/` (gitignored); only `data/aggregate/`
snapshots are committed (and only on accepted updates / monthly snapshots).

## 9. Repository structure

```
src/cs2_pro_settings/       v2 canonical pipeline (models, identity, normalize,
                            reconcile, metrics, drift, roster, scopes, report,
                            plots, cli, sources/)
config/                     cohort.yaml, sources.yaml, conclusions.yaml,
                            stability.yaml, cohort-2026-05-legacy.yaml
data/aggregate/             accepted snapshot aggregates (2026-05.json, latest.json)
reports/                    2026-05.md (historical), latest.md (generated placeholder)
docs/source-audit/          per-source policy audits
notebooks/v1/               archived 2026-05 notebook pipeline (historical only)
tests/                      offline tests + fixtures (no live scraping in CI)
social/2026-05/             historical publication drafts
.github/workflows/          ci.yml, daily-update.yml, weekly-reconcile.yml
scripts/                    actions_daily.py, actions_weekly.py
```

## 10. Historical May 2026 analysis

`reports/2026-05.md` — the original deep-dive (41 teams / 198 players,
snapshot 2026-05-05) with the cyberpunk figures in `figures/`. It is a dated,
descriptive analysis of one snapshot; prevalence does not imply causal
performance benefit. Its figures are historical; `figures/latest/` is
regenerated only when a candidate snapshot is accepted.

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
- Automated collection is restricted to sources that allow normal HTTP
  access; no anti-bot bypass is used.
- Drift thresholds are operational, not statistical.
- Roster stability guards are designed for pro-circuit reality (offseason
  moves); they are intentionally conservative.
- Interpretive/conclusion text is written by humans; the pipeline produces
  deterministic data and reports only.
