# Ranking updates (manual VRS + HLTV Top 30)

Ranking snapshots are the **manual control plane** of the v4 cohort:

- `cohort.core` is defined by the accepted **Valve Global Ranking (VRS)**
  snapshot in `config/rankings/valve/`.
- `cohort.reference` is defined by the accepted **HLTV World Ranking**
  snapshot in `config/rankings/hltv/`.

Rankings are **never scraped**. Snapshots are manually entered by
maintainers or contributors (see CONTRIBUTING.md), validated by the
importer, reviewed, and then activated by a human.

## Import

```bash
# VRS (primary Core) — provider=valve, ranking_type=global
python -m cs2_pro_settings ranking import-vrs \
  --date 2026-08-10 \
  --source-url https://www.hltv.org/valve-ranking/teams/2026/august/10 \
  --stdin < top30.txt

# HLTV (reference) — provider=hltv, ranking_type=world
python -m cs2_pro_settings ranking import-hltv \
  --date 2026-08-03 \
  --source-url https://www.hltv.org/ranking/teams/2026/august/3 \
  --stdin < top30.txt
```

Both commands share one parser/validator (`parse_top30` + `validate_entries`
+ `build_snapshot`): ranks 1–30 unique & continuous, source URL and date
required, team mapping via `config/team-mappings.yaml`.

## Activation

`activate_snapshot(path, target="core"|"reference")`:

- `target="core"` — requires a **Valve/VRS** snapshot; updates
  `cohort.core`. An HLTV snapshot CANNOT activate as Core.
- `target="reference"` — requires an **HLTV** snapshot; updates
  `cohort.reference`.

Unresolved settings source mappings do NOT invalidate a snapshot: a team
with `settings_slug: null` stays in ranking truth and only lowers
collection coverage.

## Freshness

`ranking freshness` is evaluated weekly per snapshot (Core and reference
independently): <30d fresh (status only), <90d aging (status only), <180d
stale (status only), >=180d maintenance reminder issue.

## Derived sets

consensus = VRS ∩ HLTV (27 teams, first round); ranked union = VRS ∪ HLTV
(33 teams, first round). These are computed, never hand-written.

## Hard rule

Ranking page player names are **not** imported and are **not** current
roster truth. Ranking defines competitive scope; the settings source
defines observability.
