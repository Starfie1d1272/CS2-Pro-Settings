# HLTV ranking snapshots (manual, versioned)

This directory holds **manually imported, versioned HLTV Top 30 snapshots**,
one file per ranking date: `YYYY-MM-DD.yaml`.

HLTV itself is **never scraped** by this project (anti-bot / access
limitation; bypassing it is out of scope by policy). Ranking data is entered
by maintainers or community contributors through:

- `python -m cs2_pro_settings ranking import-hltv --date ... --source-url ...`
  (validates ranks 1-30, no duplicates, continuous numbering, source URL,
  and team mapping — unresolved teams fail the import),
- or a ranking-update issue (`.github/ISSUE_TEMPLATE/ranking-update.yml`).

## Current status

**Historical snapshot awaiting structured migration.** The v1 notebooks
reference "HLTV Top 30 (2026-05-04)" but do not contain the ordered Top 30
list itself. Per project policy we do not reconstruct rankings from memory;
no `2026-05-04.yaml` is fabricated here. Until the first structured snapshot
is imported and accepted, `cohort.core.teams` stays empty and Core headline
metrics are unavailable (the legacy 2026-05 aggregate is a separate series).

## Rules

- Exactly ranks 1-30, no duplicate rank, no duplicate team, continuous
  numbering.
- `source_url` and `snapshot date` are required.
- Unresolved team mappings are reported as UNRESOLVED and block activation.
- Accepting a snapshot updates `config/cohort.yaml` `cohort.core` (provider
  `manual_hltv`, `snapshot`, `teams`).
- Ranking freshness is operational metadata only: <30d fresh, 30-89d aging,
  90-179d stale, >=180d maintenance_due (deduplicated `[maintenance]` issue
  only at >=180d). A stale ranking never blocks the settings pipeline.
