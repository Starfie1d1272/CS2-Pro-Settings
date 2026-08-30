# CS2 Professional Settings Snapshot — 2026-08

[中文版](./latest.zh-CN.md)

2026-08-30 · VRS Top 30 (2026-08-10) · 30 teams · 147 players · 130/147 settings · `vrs-core-v2`

## 1. Highlights

- **800 median eDPI** (n=130)
- **4:3** at 81.5%; **1280x960** at 69.2% (n=130 / 130)
- **Stretched scaling** at 89.2% (n=130)
- **1000 Hz polling** at 62.3%; 4000 Hz+ at 18.5% (n=130)
- **Dot + outline both off** for 82.3% (n=130)

## 2. Mouse

![mouse.png](../figures/latest/mouse.png)

- Median: **800** · Mean: **840.4** · n=130
- 600–1000 eDPI covers 70.0% of valid observations (91/130).
- Arithmetic QC: 128/130 consistent; **2 flagged** using max(2 eDPI, 1.0%) tolerance.
- DPI — 800: **50.0%** · 400: 45.4% · 1600+: 3.8% (n=130)
- Zoom sensitivity — median **1**; 1 79.1% · 1.1 4.7% · 0.8 3.9% (n=129)
- Polling — 1000: 62.3% · 2000: 19.2% · 4000: 16.2% · 8000 Hz: 2.3% (n=130)

## 3. Display

![display.png](../figures/latest/display.png)

- Aspect ratio — 4:3 81.5% · 16:9 8.5% · 5:4 6.2% (n=130)
- Resolution — 1280x960 69.2% · 1920x1080 9.2% · 1024x768 6.2% (n=130)
- Scaling mode — Stretched 89.2% · Native 6.9% · Black Bars 3.8% (n=130)
- Boost Player Contrast — enabled **83.8%** (83/99 known); disabled 16/99; missing/unknown 48/147.

## 4. Crosshair

![crosshair_geometry.png](../figures/latest/crosshair_geometry.png)

- Style codes — 4 99.2% · 5 0.8% (n=130); source-provided codes, with no mechanism interpretation.
- Size — median **1**; 1 56.2% · 2 16.9% · 1.5 8.5% (n=130)
- Gap — median **-4**; -4 43.8% · -3 22.3% · -2 6.9% (n=130)
- Thickness — median **1**; 1 53.8% · 0 30.0% · 0.1 3.8% (n=130)
- Alpha — median **255**; 255 87.7% · 200 9.2% · 250 1.5% (n=130)
- Dot enabled — **10.0%** (13/130 known)
- Outline enabled — **9.2%** (12/130 known)
- Dot and outline both disabled: **82.3%** (n=130, both fields known)

![crosshair_color.png](../figures/latest/crosshair_color.png)

- Color categories: Custom 34.1% · Green 30.2% · Cyan 27.9% · Yellow 7.8% (n=129)
- Custom RGB: **44/44** players with complete RGB (100.0%) · 21 unique exact colors · top **255,255,255** (22.7%)

## 5. Viewmodel

- `viewmodel_fov 68`: **91.0%** (n=122)
- Dominant offset: **X=2.5, Y=0, Z=-1.5**

## 6. Radar

![radar.png](../figures/latest/radar.png)

- Radar zoom — median **0.4**; 0.4 28.9% · 0.7 19.6% · 0.3 11.3% (n=97). Values are descriptive; no directional interpretation is applied.
- Radar centered enabled: 71.2% (n=118)

## 7. Extended segments

| Segment | Teams | Players | Median eDPI |
|---|---:|---:|---:|
| VRS ∩ HLTV Consensus | 27 | 132 | 800 |
| Ranked Union | 32 | 156 | 800 |
| Core + Watchlist | 33 | 161 | 800 |
| All tracked | 35 | 170 | 800 |

## 8. Changes since previous snapshot

- Previous snapshot: 2026-08-11
- Core cohort: 149 → 147 players
- Roster turnover: 0.7%
- Matched players: 147

Matched panel (same players in both snapshots):
- dpi: 0/130 changed
- edpi: 0/130 changed
- resolution: 0/130 changed
- polling_rate: 0/130 changed

## 9. Coverage & quality

| Field | valid_n / cohort |
|---|---|
| eDPI | 130 / 147 |
| DPI | 130 / 147 |
| Zoom sensitivity | 129 / 147 |
| Mouse polling rate | 130 / 147 |
| Resolution | 130 / 147 |
| Aspect ratio | 130 / 147 |
| Scaling mode | 130 / 147 |
| Boost Player Contrast | 99 / 147 |
| Crosshair color | 129 / 147 |
| Crosshair style | 130 / 147 |
| Crosshair size | 130 / 147 |
| Crosshair gap | 130 / 147 |
| Crosshair thickness | 130 / 147 |
| Crosshair alpha | 130 / 147 |
| Crosshair dot | 130 / 147 |
| Crosshair outline | 130 / 147 |
| Viewmodel FOV | 122 / 147 |
| Radar zoom | 97 / 147 |
| Radar centered | 118 / 147 |
| Radar rotating | 0 / 147 |
| Monitor refresh rate | 0 / 147 |
| fps_max | 0 / 147 |

130/147 Core players currently have at least one usable settings field.
eDPI arithmetic QC flags 2/130 comparable observations; flags remain quality signals and do not overwrite source values.

## 10. Data & code

- Snapshot date: 2026-08-30
- Source: cs2settings
- Snapshot data: [`data/aggregate/2026-08.json`](../data/aggregate/2026-08.json)
- Project & methodology: [`README.md`](../README.md)
