# CS2 Pro Settings — Latest Snapshot (generated)

> Generated deterministically by `python -m cs2_pro_settings report`.
> Interpretive conclusions require human review.

## Snapshot

- snapshot date: **2026-08-11**
- cohort size: 109 players / 24 teams
- source: v2-vrs-core
- tracked-team scope: vrs-core-v2 (35 teams in universe, 30 in Core)

## Cohort

- series: vrs-core-v2 (core_top30)
- Core ranking snapshot: 2026-08-10
- Core teams: 30
- Watchlist + Supplemental teams in universe: 5
- Core feeds headline statistics; Watchlist/Supplemental are tracked as extended segments only (see segments below).

## Source status

- cs2settings: ok

## Key metrics

- eDPI: median 800.0, mean 827.5 (n=109)
- DPI: top 800 (54.1% at 800, n=109)
- Resolution: top 1280x960 (67.9% at 1280x960, n=109)
- Aspect ratio: 4:3 80.7% (n=109)
- Refresh rate: 360Hz n/a, 540Hz+ n/a (n=0)
- fps_max 0 (unlimited): n/a (n=0)
- Crosshair: Dot+Outline off 79.8% (n=109); top color Custom
- Viewmodel: FOV 68 92.6% (n=108); dominant offset [2.5, 0.0, -1.5]
- Radar: rotating n/a (n=0), centered 69.2% (n=104)
- Polling: 4000Hz+ 15.6% (n=109)

## Comparison with previous accepted snapshot

- baseline: None -> current: 2026-08-11
- drift level: **0** (0 = data changed, no material drift; 1 = trend drift; 2 = headline conclusion changed)
- **series incompatible**: baseline series None != current series 'vrs-core-v2'; baseline incompatible — the first accepted hltv-core-v2 snapshot will initialize the new longitudinal series
- no conclusion-level changes

### Cohort change

- baseline players: 0; current: 109
- added: 109; removed: 0

### Matched panel

- status: unavailable; matched: 0

## Source conflicts

- total: 0

## Roster stability

- status: warmup (previous None / current 154 / matched None)
- turnover rate: None (operational threshold 15% in config/stability.yaml)

## Extended tracking (non-Core segments)

- core_plus_watchlist: 123 players / 27 teams (eDPI median 800.0)
- all_tracked: 154 players / 35 teams (eDPI median 800.0)

## Limitations

- All statements describe the sampled cohort; prevalence does not imply causal performance benefit.
- valid_n varies per field; a missing field never defaults to the full cohort size.
- Automated collection is limited to target paths that are accessible via ordinary HTTP and are not disallowed for the configured user agent by the source's robots policy; a robots allowance or absence of dedicated terms is NOT affirmative legal permission.
- Row-level third-party data is not distributed; only aggregates and generated analyses are published.
- Runtime state (roster/matched-panel) is best-effort operational state via the Actions cache; cache loss causes a safe warm-up run, not a false drift alert.
