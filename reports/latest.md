# CS2 Pro Settings — Latest Snapshot (generated)

> Generated deterministically by `python -m cs2_pro_settings report`.
> Interpretive conclusions require human review.

## Snapshot

- snapshot date: **2026-08-11**
- cohort size: 133 players / 30 teams
- source: v2-vrs-core
- tracked-team scope: vrs-core-v2 (37 teams in universe, 30 in Core)

## Cohort

- series: vrs-core-v2 (core_top30)
- Core ranking snapshot: 2026-08-10
- Core teams: 30
- Watchlist + Supplemental teams in universe: 7
- Core feeds headline statistics; Watchlist/Supplemental are tracked as extended segments only (see segments below).

## Source status

- cs2settings: ok

## Key metrics

- eDPI: median 800.0, mean 844.3 (n=133)
- DPI: top 800 (50.4% at 800, n=133)
- Resolution: top 1280x960 (68.4% at 1280x960, n=133)
- Aspect ratio: 4:3 82.0% (n=133)
- Refresh rate: 360Hz n/a, 540Hz+ n/a (n=0)
- fps_max 0 (unlimited): n/a (n=0)
- Crosshair: Dot+Outline off 80.5% (n=133); top color Custom
- Viewmodel: FOV 68 91.2% (n=125); dominant offset [2.5, 0.0, -1.5]
- Radar: rotating n/a (n=0), centered 71.7% (n=120)
- Polling: 4000Hz+ 18.1% (n=133)

## Comparison with previous accepted snapshot

- baseline: 2026-05-05 -> current: 2026-08-11
- drift level: **0** (0 = data changed, no material drift; 1 = trend drift; 2 = headline conclusion changed)
- **series incompatible**: baseline series 'legacy-top30-plus-selected-v1' != current series 'vrs-core-v2'; baseline incompatible — the first accepted vrs-core-v2 snapshot will initialize the new longitudinal series
- **scope changed**: scope metadata changed (legacy baseline); headline Level 2 suppressed
- **headline suppressed**: scope metadata changed (legacy baseline); headline Level 2 suppressed
- no conclusion-level changes

### Cohort change

- baseline players: 198; current: 133
- added: 11; removed: 11

### Matched panel

- status: unavailable; matched: 0
- no overlap between previous runtime panel and current panel

## Source conflicts

- total: 0

## Roster stability

- status: warmup (previous None / current 172 / matched None)
- turnover rate: None (operational threshold 15% in config/stability.yaml)

## Extended tracking (non-Core segments)

- core_plus_watchlist: 147 players / 33 teams (eDPI median 800.0)
- all_tracked: 154 players / 35 teams (eDPI median 800.0)

## Limitations

- All statements describe the sampled cohort; prevalence does not imply causal performance benefit.
- valid_n varies per field; a missing field never defaults to the full cohort size.
- Automated collection is limited to target paths that are accessible via ordinary HTTP and are not disallowed for the configured user agent by the source's robots policy; a robots allowance or absence of dedicated terms is NOT affirmative legal permission.
- Row-level third-party data is not distributed; only aggregates and generated analyses are published.
- Runtime state (roster/matched-panel) is best-effort operational state via the Actions cache; cache loss causes a safe warm-up run, not a false drift alert.
