# CS2 Pro Settings Tracker

[English](README.md) | [简体中文](./README.zh-CN.md)

**What settings do top CS2 professionals actually use — and how do those choices change over time?**

CS2 Pro Settings Tracker turns professional-player settings into a reproducible longitudinal dataset.

Instead of publishing another static settings table, the project tracks the current VRS Top 30, follows roster changes and stable player identities, records accepted monthly snapshots, and separates real same-player setting changes from changes caused by roster turnover.

## Current snapshot

<!-- CURRENT_SNAPSHOT:START -->
**2026-08-11 · VRS Top 30 · 30 teams · 149 players** — the first accepted `vrs-core-v2` baseline.

- 133/149 players with usable settings (89.3%)
- median eDPI 800
- 400 + 800 DPI = 95.5%
- 4:3 = 82.0%
- 1280x960 = 68.4%
- 1000 Hz = 62.4%
- 4000 Hz+ = 18.0%
- viewmodel_fov 68 = 91.2%
<!-- CURRENT_SNAPSHOT:END -->

From the current snapshot, 800 eDPI, 4:3, 1280×960 and FOV 68 still form a remarkably stable picture of the pro-scene mainstream.

→ [Latest report](./reports/latest.md) · [中文报告](./reports/latest.zh-CN.md) · [Monthly archive](./reports/2026-08.md)

## Why this project exists

Static pro-settings websites answer one question well: *"what does this player use right now?"* This project answers a different one: **how do the settings preferences of the entire pro scene change over time?**

- Is 800 DPI continuing to replace 400 DPI?
- Will 4:3 actually leave the pro scene?
- Will 4K/8K polling rates become the new standard?
- Does a change in the data mean the scene changed, or just that different players entered the Top 30?
- Which parameters do the *same* players adjust months later?

A one-off static table cannot answer these. That is why this project evolved from a single May 2026 analysis into a scheduled longitudinal tracker.

## From one analysis to a long-term tracker

The first community article (小黑盒, published 2026-05-05) analyzed 41 teams / 198 players and drew strong feedback. Manually recorded engagement snapshot (captured 2026-08-11; **not** auto-updated):

- 2852 likes
- 4408 favorites
- 402 comments

The feedback pushed the project from a one-off analysis into the automated tracker you see here. Record: [`social/2026-05/publication.md`](./social/2026-05/publication.md)

## What makes the tracker different?

### Stable player identities
Players are identified by SteamID (`steam:<id>`), never by a bare nickname, so the same person is tracked across time and across sources.

### Roster-aware tracking
The Core sample is the accepted VRS Top 30. Rosters are tracked per team with stable IDs, and roster turnover is kept separate from settings changes.

### Same-player longitudinal panel
When the same player appears in two snapshots, their fields are compared directly. `missing → value` / `value → missing` transitions are completeness changes, not settings changes.

### Reproducible monthly snapshots
Every accepted month is archived as machine-readable aggregate (`data/aggregate/`) plus deterministic bilingual reports (`reports/latest.md` / `reports/YYYY-MM.md`, English + zh-CN).

### Automated but review-gated
Collection, drift detection and candidate PRs are automated; nothing is auto-merged. Reports are deterministic and no LLM is used to invent conclusions.

## How it works

```
VRS Top 30 (accepted ranking snapshot)
  ↓
Current roster (per-team, stable IDs)
  ↓
Stable SteamID identity
  ↓
Settings collection (normal HTTP, fail closed)
  ↓
Normalization / reconciliation (conflicts surfaced, never overwritten)
  ↓
Monthly snapshots (accepted aggregates + bilingual reports)
  ↓
Current-cohort + matched-player analysis
  ↓
Reports / community articles
```

## Cohort model

- **Core (primary)**: accepted Valve Global Ranking (VRS) Top 30 snapshot — manual import, never scraped.
- **Reference**: accepted HLTV World Ranking Top 30 (sensitivity panel).
- **Segments**: consensus (VRS ∩ HLTV), ranked union (VRS ∪ HLTV), Core + Watchlist, all tracked — reported only when real values exist.
- **Series compatibility**: `vrs-core-v2` (from 2026-08) is the current longitudinal series. The 2026-05 legacy snapshot (`legacy-top30-plus-selected-v1`, 41 teams / 198 players) is a historical reference and is **not** treated as a directly comparable baseline.
- Ranking truth and settings-source coverage are independent: an unresolved source mapping lowers collection coverage only, never the ranking.

## Automation & review gates

- **CI**: offline pytest (warnings-as-errors) + offline fixture end-to-end + deterministic-output check on every PR.
- **Daily**: source health → scope → roster → settings → metrics → drift; deduplicated issues; candidate PR only on Level 2 with stable scope and roster.
- **Weekly**: quality/maintenance checks, ranking freshness, monthly-snapshot due check.
- **Monthly**: missing or stale `data/aggregate/YYYY-MM.json` triggers a candidate that synchronizes all four report files (`latest.md`, `latest.zh-CN.md`, `YYYY-MM.md`, `YYYY-MM.zh-CN.md`) — latest is never newer than the same-month archive.
- Nothing auto-merges; issues and candidate PRs are deduplicated.

## Drift rules

Deterministic rules in `config/conclusions.yaml` (no LLM): Level 1 = share moves ≥ 5 pp (or eDPI median ≥ 50); Level 2 = dominant category flips. When Core roster turnover ≥ 15% or the Core scope changed, the overall headline Level 2 is suppressed pending human review. These are **operational notification thresholds, not statistical significance**.

## Source policy

| Source | Roster discovery | Player settings | Stable identity | Scheduled | Local review |
|---|---|---|---|---|---|
| cs2settings.com | yes | yes | yes | yes | yes |
| prosettings.net | no | yes | yes (numeric /profiles/) | **no** | yes |
| proconfig.net | no | yes | yes | no (disabled) | opt-in |

Per-source audits: `docs/source-audit/`. Only ordinary HTTP; no anti-bot bypass, CAPTCHA solving, proxy rotation, or browser automation. Third-party row-level data is not redistributed (`DATA_PROVENANCE.md`).

## Reproduce locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -v                          # offline tests
python -m cs2_pro_settings update --offline  # full pipeline on fixtures
python -m cs2_pro_settings update --scheduled  # live pipeline, scheduled sources
python scripts/render_accepted.py            # backfill first-baseline / re-render latest pair
```

## Repository structure

```
src/cs2_pro_settings/    v2 pipeline (identity, cohort, roster, metrics, drift,
                         report, plots, sources, ...)
config/                  cohort.yaml, sources.yaml, conclusions.yaml,
                         stability.yaml, team-mappings.yaml, rankings/
data/aggregate/          accepted snapshots (2026-05.json, 2026-08.json, latest.json)
reports/                 deterministic bilingual reports (latest.*, YYYY-MM.*;
                         2026-05.md = preserved historical legacy)
figures/                 deterministic headline figures
social/                  human/editorial publication archive (never modified
                         by automation) + publication records
scripts/                 actions_*.py (automation), render_accepted.py
tests/                   offline tests + fixtures
```

## Historical May 2026 analysis

`reports/2026-05.md` is the original deep-dive (41 teams / 198 players, snapshot 2026-05-05). It is a dated, descriptive analysis of one snapshot and is preserved in its original form — the standardized bilingual reports begin with 2026-08.

## Licensing

- Source code: MIT (`LICENSE`).
- Reports, docs, generated figures: CC BY 4.0 (`CONTENT_LICENSE.md`).
- Third-party source data: not relicensed by this repository (`DATA_PROVENANCE.md`).

## Data notes

- Field-level `valid_n` may differ; a missing field never defaults to the full cohort size.
- The 2026-05 legacy series (`legacy-top30-plus-selected-v1`) is a historical reference, not a same-series longitudinal baseline for `vrs-core-v2`.
