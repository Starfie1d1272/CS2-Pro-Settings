# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project

CS2 Pro Settings Tracker — a reproducible, multi-source longitudinal data
pipeline for tracking how professional Counter-Strike 2 settings evolve over
time. v1 was a one-off May 2026 notebook analysis; v2 is the canonical
automated pipeline.

## v1 vs v2

- `notebooks/v1/` — historical 2026-05 snapshot pipeline. **Historical only**;
  not executed by CI, not scheduled, do not modify their algorithms.
- `src/cs2_pro_settings/` — **canonical v2 pipeline** (models, identity,
  cohort, normalize, reconcile, metrics, drift, roster, rankings,
  runtime_state, scopes, report, plots, CLI, sources).
- `reports/2026-05.md` — historical snapshot analysis (dated, descriptive).
- `reports/latest.md` — generated placeholder; regenerated only when a
  candidate snapshot is accepted.

## Environment

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"        # canonical dependency source: pyproject.toml
python -m pytest -v            # offline tests (no live scraping)
python -m cs2_pro_settings update --offline   # offline fixture pipeline
```

Do NOT use machine-specific paths.

## Pipeline order (also the decision order for automation)

1. source health → 2. ranking/core scope → 3. current roster → 4. settings
   collect → 5. normalize → 6. reconcile → 7. metrics → 8. stability →
   9. drift → 10. report

Automation rules:

- CI is offline: pytest + offline fixture pipeline + deterministic check.
- Scheduled workflows are online but only for enabled sources.
- HLTV rankings are MANUAL (imported snapshots, never scraped).
- Core scope unstable OR roster unstable (turnover >= 15%) → overall
  headline Level 2 automation is suppressed (human review required); the
  matched panel is always computed independently.
- A baseline from a different cohort series (legacy 2026-05 vs hltv-core-v2)
  is NOT comparable for headline Level 1/2 automation.
- Cross-run runtime state (roster baseline, previous matched panel) lives in
  `.runtime-state/` (gitignored) and persists via the GitHub Actions cache;
  cache loss → safe warm-up run.
- Raw third-party source data / raw HTML is never committed; `work/` and
  `.runtime-state/` are gitignored; only `data/aggregate/` snapshots are
  committed.
- Issues and candidate PRs are deduplicated; nothing is auto-merged.
- Report interpretation is written by humans; the pipeline is deterministic.
- No anti-bot bypass, CAPTCHA solving, proxy rotation, or browser automation.

## Data rules

- Every aggregate share carries `valid_n`; a missing field never defaults to
  the full cohort size.
- Player identity: `steam:<steamid>` preferred; never a bare nickname.
- Reconciliation surfaces conflicts; never silently overwrite.
- 5pp / 15% thresholds are operational notification thresholds, not
  statistical significance.

## Cohort model v3

- **Core**: strictly defined by the last accepted manual HLTV Top 30
  snapshot (`config/rankings/hltv/YYYY-MM-DD.yaml`); Core only feeds
  headline statistics.
- **Watchlist**: manual near-top30 / rising teams (not proof of HLTV rank).
- **Supplemental**: regional / notable / legacy-selected teams.
- Tracked universe = Core ∪ Watchlist ∪ Supplemental; extended segments are
  reported separately (`segments` in metrics).
- `ranking import-hltv` validates 1..30 unique/continuous ranks + mapping;
  unresolved teams fail or emit non-activatable candidates.

## Key files

- `config/cohort.yaml` — Core/Watchlist/Supplemental + filters
- `config/sources.yaml` — source enablement + field priority
- `config/conclusions.yaml` — deterministic drift rules
- `config/stability.yaml` — roster turnover guard (15%)
- `config/team-mappings.yaml` — ranking display name → slug mapping
- `docs/source-audit/` — per-source policy audits
- `DATA_PROVENANCE.md` — third-party data boundaries + runtime state
- `CONTRIBUTING.md`, `docs/ranking-updates.md` — community ranking updates
