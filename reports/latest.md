# CS2 Pro Settings — Latest Snapshot (generated)

> Generated deterministically by `python -m cs2_pro_settings report`.
> Interpretive conclusions require human review.

## Snapshot

- snapshot date: **2026-08-10**
- cohort size: 0 players / 0 teams
- source: v2-core
- tracked-team scope: top-tier-plus-selected-v1 (30 teams in universe, 0 in Core)

## Cohort

- series: hltv-core-v2 (core_top30)
- Core ranking snapshot: none accepted yet
- Core teams: 0
- Watchlist + Supplemental teams in universe: 30
- Core feeds headline statistics; Watchlist/Supplemental are tracked as extended segments only (see segments below).

## Source status

- cs2settings: ok
- prosettings: ok

## Key metrics

- eDPI: median None, mean None (n=0)
- DPI: top None (n/a at 800, n=0)
- Resolution: top None (n/a at 1280x960, n=0)
- Aspect ratio: 4:3 n/a (n=0)
- Refresh rate: 360Hz n/a, 540Hz+ n/a (n=0)
- fps_max 0 (unlimited): n/a (n=0)
- Crosshair: Dot+Outline off n/a (n=0); top color None
- Viewmodel: FOV 68 n/a (n=0); dominant offset None
- Radar: rotating n/a, centered n/a (n=0)
- Polling: 4000Hz+ n/a (n=0)

## Comparison with previous accepted snapshot

- baseline: None -> current: 2026-08-10
- drift level: **0** (0 = data changed, no material drift; 1 = trend drift; 2 = headline conclusion changed)
- **series incompatible**: baseline series None != current series 'hltv-core-v2'; baseline incompatible — the first accepted hltv-core-v2 snapshot will initialize the new longitudinal series
- **scope changed**: tracked-team scope changed between baseline and current snapshot; overall cohort conclusion flips are NOT judged as Level 2 — scope change requires human review (matched-panel comparison only)
- cohort stability: stable (roster turnover 0.0)
- **headline suppressed**: tracked-team scope changed
- no conclusion-level changes

### Cohort change

- baseline players: 0; current: 0
- added: 0; removed: 0

### Matched panel

- status: unavailable; matched: 0

## Source conflicts

- total: 0

## Roster stability

- status: compared (previous 3 / current 3 / matched 3)
- turnover rate: 0.0 (operational threshold 15% in config/stability.yaml)

## Extended tracking (non-Core segments)

- core_plus_watchlist: 0 players / 0 teams (eDPI median None)
- all_tracked: 3 players / 1 teams (eDPI median 800.0)

## Limitations

- All statements describe the sampled cohort; prevalence does not imply causal performance benefit.
- valid_n varies per field; a missing field never defaults to the full cohort size.
- Automated collection is limited to target paths that are accessible via ordinary HTTP and are not disallowed for the configured user agent by the source's robots policy; a robots allowance or absence of dedicated terms is NOT affirmative legal permission.
- Row-level third-party data is not distributed; only aggregates and generated analyses are published.
- Runtime state (roster/matched-panel) is best-effort operational state via the Actions cache; cache loss causes a safe warm-up run, not a false drift alert.
