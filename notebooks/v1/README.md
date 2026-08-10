# v1 Notebook Pipeline (historical)

These notebooks implement the original **2026-05 snapshot** pipeline:

- `01_data_collection.ipynb` — scrape prosettings.net list + player detail pages → raw CSVs
- `02_data_cleaning.ipynb` — ETL cleaning + quality checks + feature enrichment → Final CSV
- `03_final_report.ipynb` — render the 22 analysis figures (cyberpunk theme) → `figures/`

## Status

- Retained **for historical reproducibility** only.
- Cell outputs were cleared: the archived versions contain code and markdown, not
  third-party scraped row-level data.
- The v2 production pipeline lives under `src/cs2_pro_settings/` and is the
  canonical automated pipeline.
- These notebooks are **no longer the canonical automated pipeline**. They are not
  executed by CI, not scheduled, and their source code is frozen (no algorithm
  changes; do not modify them as part of v2 development).

## Historical inputs/outputs

The row-level CSV outputs (`cs2_pro_raw.csv`, `cs2_pro_detailed_RAW.csv`,
`cs2_pro_2026_Active_Master.csv`, `cs2_pro_2026_Active_Final.csv`) are no longer
distributed in the current public tree. The aggregate statistics they produced are
preserved in `data/aggregate/2026-05.json`.
