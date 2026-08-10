# AGENTS.md

This file provides guidance to AI coding agents (Codex, Claude Code, etc.)
when working with this repository.

## Project

CS2 Pro Settings Tracker — a reproducible, multi-source longitudinal data
pipeline for tracking how professional Counter-Strike 2 settings evolve over
time. v1 was a one-off May 2026 notebook analysis; v2 is the canonical
automated pipeline.

## v1 vs v2

- `notebooks/v1/` — historical 2026-05 snapshot pipeline. **Historical only**;
  not executed by CI, not scheduled, do not modify their algorithms.
- `src/cs2_pro_settings/` — **canonical v2 pipeline** (identity, normalize,
  reconcile, metrics, drift, roster, scopes, report, plots, CLI, sources).
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

Do NOT use machine-specific paths (e.g. `/opt/homebrew/Caskroom/...`).

## Pipeline order (also the decision order for automation)

1. source health → 2. current team scope → 3. current roster → 4. settings
   collect → 5. normalize → 6. reconcile → 7. metrics → 8. stability → 9. drift
   → 10. report

Automation rules:

- CI is offline: pytest + offline fixture pipeline + deterministic check.
- Scheduled workflows are online but only for enabled sources.
- scope unstable OR roster unstable (turnover >= 15%) → overall Level 2
  headline automation is suppressed (human review required); matched panel is
  always computed independently.
- Raw third-party source data / raw HTML is never committed; `work/` is
  gitignored; only `data/aggregate/` snapshots are committed.
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

## Key files

- `config/sources.yaml` — source enablement + field priority
- `config/cohort.yaml` — tracked-team scope (explicit, versioned)
- `config/conclusions.yaml` — deterministic drift rules
- `config/stability.yaml` — roster turnover guard (15%)
- `docs/source-audit/` — per-source policy audits
- `DATA_PROVENANCE.md` — third-party data boundaries
