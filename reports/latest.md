# CS2 Professional Settings Snapshot — 2026-08

[中文版](./latest.zh-CN.md)

2026-08-16 · VRS Top 30 (2026-08-10) · 30 teams · 149 players · 132/149 settings · `vrs-core-v2`

## 1. Highlights

- **800 median eDPI** (n=132)
- **4:3** at 81.8%; **1280x960** at 68.9% (n=132 / 132)
- **Stretched scaling** at 89.4% (n=132)
- **1000 Hz polling** at 62.1%; 4000 Hz+ at 18.2% (n=132)
- **Dot + outline both off** for 81.8% (n=132)

## 2. Mouse

![mouse.png](../figures/latest/mouse.png)

- Median: **800** · Mean: **843.7** · n=132
- 600–1000 eDPI covers 69.7% of valid observations (92/132).
- Arithmetic QC: 130/132 consistent; **2 flagged** using max(2 eDPI, 1.0%) tolerance.
- DPI — 800: **50.0%** · 400: 45.5% · 1600+: 3.8% (n=132)
- Zoom sensitivity — median **1**; 1 77.9% · 1.1 4.6% · 0.8 3.8% (n=131)
- Polling — 1000: 62.1% · 2000: 19.7% · 4000: 15.9% · 8000 Hz: 2.3% (n=132)

## 3. Display

![display.png](../figures/latest/display.png)

- Aspect ratio — 4:3 81.8% · 16:9 8.3% · 5:4 6.1% (n=132)
- Resolution — 1280x960 68.9% · 1920x1080 9.1% · 1024x768 6.8% (n=132)
- Scaling mode — Stretched 89.4% · Native 6.8% · Black Bars 3.8% (n=132)
- Boost Player Contrast — enabled **84.0%** (84/100 known); disabled 16/100; missing/unknown 49/149.

## 4. Crosshair

![crosshair_geometry.png](../figures/latest/crosshair_geometry.png)

- Style codes — 4 99.2% · 5 0.8% (n=132); source-provided codes, with no mechanism interpretation.
- Size — median **1**; 1 56.1% · 2 18.2% · 1.5 6.8% (n=132)
- Gap — median **-4**; -4 42.4% · -3 23.5% · -2 6.1% (n=132)
- Thickness — median **1**; 1 53.8% · 0 25.8% · 0.5 5.3% (n=132)
- Alpha — median **255**; 255 78.0% · 200 20.5% · 175 0.8% (n=132)
- Dot enabled — **9.8%** (13/132 known)
- Outline enabled — **9.1%** (12/132 known)
- Dot and outline both disabled: **81.8%** (n=132, both fields known)

![crosshair_color.png](../figures/latest/crosshair_color.png)

- Color categories: Custom 37.4% · Cyan 32.1% · Green 22.9% · Yellow 7.6% (n=131)
- Custom RGB: **49/49** players with complete RGB (100.0%) · 23 unique exact colors · top **0,255,255** (16.3%)

## 5. Viewmodel

- `viewmodel_fov 68`: **91.1%** (n=124)
- Dominant offset: **X=2.5, Y=0, Z=-1.5**

## 6. Radar

![radar.png](../figures/latest/radar.png)

- Radar zoom — median **0.4**; 0.4 28.6% · 0.7 19.4% · 0.3 11.2% (n=98). Values are descriptive; no directional interpretation is applied.
- Radar centered enabled: 71.4% (n=119)

## 7. Extended segments

| Segment | Teams | Players | Median eDPI |
|---|---:|---:|---:|
| VRS ∩ HLTV Consensus | 27 | 134 | 800 |
| Ranked Union | 32 | 158 | 800 |
| Core + Watchlist | 33 | 163 | 800 |
| All tracked | 35 | 172 | 800 |

## 8. Changes since previous snapshot

- Previous snapshot: 2026-08-11
- Core cohort: 149 → 149 players
- Roster turnover: 0.0%
- Matched players: 149

Matched panel (same players in both snapshots):
- dpi: 0/132 changed
- edpi: 0/132 changed
- resolution: 0/132 changed
- polling_rate: 0/132 changed

## 9. Coverage & quality

| Field | valid_n / cohort |
|---|---|
| eDPI | 132 / 149 |
| DPI | 132 / 149 |
| Zoom sensitivity | 131 / 149 |
| Mouse polling rate | 132 / 149 |
| Resolution | 132 / 149 |
| Aspect ratio | 132 / 149 |
| Scaling mode | 132 / 149 |
| Boost Player Contrast | 100 / 149 |
| Crosshair color | 131 / 149 |
| Crosshair style | 132 / 149 |
| Crosshair size | 132 / 149 |
| Crosshair gap | 132 / 149 |
| Crosshair thickness | 132 / 149 |
| Crosshair alpha | 132 / 149 |
| Crosshair dot | 132 / 149 |
| Crosshair outline | 132 / 149 |
| Viewmodel FOV | 124 / 149 |
| Radar zoom | 98 / 149 |
| Radar centered | 119 / 149 |
| Radar rotating | 0 / 149 |
| Monitor refresh rate | 0 / 149 |
| fps_max | 0 / 149 |

132/149 Core players currently have at least one usable settings field.
eDPI arithmetic QC flags 2/132 comparable observations; flags remain quality signals and do not overwrite source values.

## 10. Data & code

- Snapshot date: 2026-08-16
- Source: cs2settings
- Snapshot data: [`data/aggregate/2026-08.json`](../data/aggregate/2026-08.json)
- Project & methodology: [`README.md`](../README.md)
