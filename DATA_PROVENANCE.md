# Data Provenance

## Sources

This project tracks professional CS2 player settings published by third-party
websites:

- prosettings.net — player settings database (used by the original 2026-05 snapshot)
- cs2settings.com — player settings database (v2 primary candidate source)
- proconfig.gg — editorial cross-check source (v2 secondary, disabled by default)

## Ownership

- Third-party source data is **not relicensed by this repository**. Upstream
  rights remain with their respective sources.
- **Source-derived row-level datasets are not distributed in the current
  public tree.** The row-level CSVs from the original 2026-05 snapshot
  (`cs2_pro_raw.csv`, `cs2_pro_detailed_RAW.csv`,
  `cs2_pro_2026_Active_Master.csv`, `cs2_pro_2026_Active_Final.csv`) were
  removed when the v2 pipeline was introduced. They may remain in Git history
  for transparency; the current public tree no longer republishes them.
- Raw scraped HTML is never committed or uploaded as artifacts.
- No live crawl output (work/) is committed.

## What is published

- **Aggregate statistics** (`data/aggregate/`) — per-snapshot summary metrics
  with `valid_n` for every denominator. These are derived statistics over the
  sampled cohort, not third-party row-level records.
- **Reports** (`reports/`) — descriptive analyses authored from aggregate
  statistics, with explicit snapshot date and cohort scope.
- Generated figures (`figures/`) — visualizations of aggregate statistics.

Every aggregate snapshot records its source and generation date. Every
normalized field in the v2 pipeline carries provenance (source, source_url,
retrieved_at, source_updated_at where available).

## Policy

Automated collection is limited to sources that permit normal HTTP access and
do not block automated requests. Adapters fail closed; no anti-bot bypass,
CAPTCHA solving, proxy rotation, or browser automation is used. See
`docs/source-audit/` for per-source policy audits.
