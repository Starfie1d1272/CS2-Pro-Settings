# Ranking updates (manual HLTV Top 30)

HLTV ranking snapshots are the **manual control plane** of the v2 cohort:
`cohort.core` is defined only by the last accepted structured snapshot in
`config/rankings/hltv/YYYY-MM-DD.yaml`. Downstream roster/settings
collection is the automated data plane.

## Why manual?

HLTV uses anti-bot / access limitation. This project will **not** bypass it.
Rankings are therefore entered by humans (maintainers or contributors) and
reviewed before activation. Dynamic ranking-based scope remains a planned
extension only.

## Importing

```bash
python -m cs2_pro_settings ranking import-hltv \
  --date 2026-08-10 \
  --source-url https://www.hltv.org/ranking/1/2026/august/10 \
  --stdin
```

Input format (stdin or --file):

```
1 Vitality
2 Spirit
3 The MongolZ
...
30 GamerLegion
```

Validation (importer fails on any violation):

- exactly 30 teams;
- ranks are exactly 1..30, unique and continuous;
- no duplicate team names;
- `--source-url` (http/https) and `--date` (ISO) required;
- every display name resolves in `config/team-mappings.yaml`; unresolved
  teams print `UNRESOLVED` and the import fails (or, with
  `--allow-unresolved`, emits a candidate marked `unresolved: true` that
  **cannot be activated**).

Output: `config/rankings/hltv/YYYY-MM-DD.yaml` (candidate).

## Comparing with the previous ranking

```bash
python -m cs2_pro_settings ranking import-hltv \
  --date ... --source-url ... --stdin \
  --previous config/rankings/hltv/2026-05-04.yaml
```

Prints `ENTERED CORE`, `EXITED CORE`, `RANK MOVEMENTS` and review
suggestions. Exiting Core does **not** delete historical tracking data; it
produces a watchlist-review suggestion for the maintainer.

## Activation (human step)

The accepted snapshot must be fully resolved (no `unresolved` entries and
every team with a `settings_slug`). Activation updates `config/cohort.yaml`
`cohort.core`:

```python
from cs2_pro_settings.rankings import activate_snapshot
activate_snapshot(Path("config/rankings/hltv/2026-08-10.yaml"))
```

## Freshness

- <30 days: fresh
- 30–89 days: aging (status only)
- 90–179 days: stale (status only)
- ≥180 days: maintenance_due → deduplicated `[maintenance]` issue

A stale ranking never blocks the settings pipeline; the generated report
always names the accepted ranking date.
