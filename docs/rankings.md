# Ranking control plane — accepted snapshots

Rankings are **manually imported** (never scraped; HLTV anti-bot / access
limitation is out of scope by policy). The two accepted snapshots define the
v4 cohort:

## Valve Global Ranking (VRS) — PRIMARY CORE

- snapshot date: **2026-08-10**
- ranking_provider: **Valve** (Valve is the ranking authority)
- page_host: **hltv.org** (HLTV hosts a display page; HLTV does NOT author
  the Valve ranking)
- source URL: https://www.hltv.org/valve-ranking/teams/2026/august/10
- file: `config/rankings/valve/2026-08-10.yaml`

VRS is the chosen PRIMARY competitive scope for this project — a project
methodology decision, not a claim that any other ranking is useless.

## HLTV World Ranking — REFERENCE / sensitivity

- snapshot date: **2026-08-03**
- ranking_provider: **HLTV** (authority AND host)
- source URL: https://www.hltv.org/ranking/teams/2026/august/3
- file: `config/rankings/hltv/2026-08-03.yaml`

## Derived sets (computed, not hand-written)

- consensus = VRS ∩ HLTV = 27 teams
- ranked union = VRS ∪ HLTV = 33 teams
- HLTV-only: paiN, 3DMAX, Luminosity
- VRS-only: Inner Circle, HOTU, EYEBALLERS

## Hard invariant

Ranking defines **competitive scope**; the settings source defines
**observability**. An unresolved settings source mapping lowers collection
coverage only — it never invalidates a ranking. Player names printed on
ranking pages are NOT imported and are NOT current roster truth.
