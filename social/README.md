# social/

This directory is the **cross-period publication archive** for
human-written, editorial, platform-specific drafts and publication records.

It is the third layer of the project's report stack:

1. `data/aggregate/` — machine-readable accepted data (deterministic).
2. `reports/` — deterministic bilingual snapshot reports (auto-generated).
3. `social/` — human/editorial publications (this directory).

## Policy

- **Scheduled automation (daily/weekly workflows) never modifies anything
  under `social/`.** The candidate-writer only touches
  `data/aggregate/`, `reports/` and `figures/`.
- Each period may contain any of:
  `heybox-article.md`, `bilibili.md`, `xiaohongshu.md`, `wechat.md`, etc.
  Files are created only when actually needed — not every platform is
  required for every period.
- Article numbers **must come from the accepted snapshot** (`data/aggregate/`
  + `reports/`). Publication prose may be reorganized freely, but numbers
  from different series (e.g. the 2026-05 legacy cohort vs `vrs-core-v2`)
  must never be presented as a strict longitudinal trend.
- `publication.md` records publication metadata (platform, date, URL) and
  **manually captured** engagement snapshots. Engagement figures are never
  scraped or auto-updated.

## Periods

- `2026-05/` — first publication (2026-05-05, Heybox), historical article
  preserved in its original form.
- `2026-08/` — second publication period (Heybox article scaffold + this
  period's publication record when published).
