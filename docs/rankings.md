# Ranking control plane — accepted snapshots

Rankings are **manually imported** (never scraped; HLTV anti-bot / access
limitation is out of scope by policy). The two accepted snapshots define the
v4 cohort:

## Valve Global Ranking (VRS) — PRIMARY CORE

- snapshot date: **2026-11-02**
- ranking_provider: **Valve** (Valve is the ranking authority)
- page_host: **github.com** (official ValveSoftware standings repository)
- source URL: https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_11_02.md
- file: `config/rankings/valve/2026-11-02.yaml` (historical: `2026-08-10.yaml`)

VRS is the chosen PRIMARY competitive scope for this project — a project
methodology decision, not a claim that any other ranking is useless.

## HLTV World Ranking — REFERENCE / sensitivity

- snapshot date: **2026-08-03** (retained as historical reference; not used for current ranking claims)
- ranking_provider: **HLTV** (authority AND host)
- source URL: https://www.hltv.org/ranking/teams/2026/august/3
- file: `config/rankings/hltv/2026-08-03.yaml`

## Derived sets (computed, not hand-written)

- consensus = VRS ∩ HLTV = 22 teams
- ranked union = VRS ∪ HLTV = 38 teams
- HLTV-only (vs 2026-08-03 reference): 3DMAX, Alliance, BIG, GamerLegion, Luminosity, magic, paiN, TyLoo
- VRS-only (2026-11-02): 100 Thieves, 1win, Eternal Fire, fnatic, HOTU, Inner Circle, M80, Nemiga

## Hard invariant

Ranking defines **competitive scope**; the settings source defines
**observability**. An unresolved settings source mapping lowers collection
coverage only — it never invalidates a ranking. Player names printed on
ranking pages are NOT imported and are NOT current roster truth.
