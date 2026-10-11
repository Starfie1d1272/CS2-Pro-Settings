# CS2 Professional Settings Snapshot — 2026-10

[中文版](./latest.zh-CN.md)

2026-10-11 · VRS Top 30 (2026-08-10) · 30 teams · 149 players · 132/149 settings · `vrs-core-v2`

## 1. Highlights

- **800 median eDPI** (n=132)
- **4:3** at 81.1%; **1280x960** at 66.7% (n=132 / 132)
- **Stretched scaling** at 87.9% (n=132)
- **1000 Hz polling** at 65.2%; 4000 Hz+ at 15.9% (n=132)
- **Dot + outline both off** for 84.1% (n=132)

## 2. Mouse

![mouse.png](../figures/latest/mouse.png)

- Median: **800** · Mean: **832.1** · n=132
- 600–1000 eDPI covers 68.9% of valid observations (91/132).
- Arithmetic QC: 130/132 consistent; **2 flagged** using max(2 eDPI, 1.0%) tolerance.
- DPI — 800: **50.8%** · 400: 44.7% · 1600+: 3.8% (n=132)
- Zoom sensitivity — median **1**; 1 77.9% · 1.1 5.3% · 0.8 3.8% (n=131)
- Polling — 1000: 65.2% · 2000: 18.9% · 4000: 13.6% · 8000 Hz: 2.3% (n=132)

## 3. Display

![display.png](../figures/latest/display.png)

- Aspect ratio — 4:3 81.1% · 16:9 9.1% · 5:4 6.1% (n=132)
- Resolution — 1280x960 66.7% · 1920x1080 9.8% · 1024x768 7.6% (n=132)
- Scaling mode — Stretched 87.9% · Native 7.6% · Black Bars 4.5% (n=132)
- Boost Player Contrast — enabled **83.8%** (83/99 known); disabled 16/99; missing/unknown 50/149.

## 4. Crosshair

![crosshair_geometry.png](../figures/latest/crosshair_geometry.png)

- Style codes — 4 97.7% · 3 1.5% · 5 0.8% (n=132); source-provided codes, with no mechanism interpretation.
- Size — median **2**; 2 53.8% · 4 15.2% · 3 14.4% (n=132)
- Gap — median **1**; 1 42.4% · 2 22.7% · 0 14.4% (n=132)
- Thickness — median **2**; 2 55.3% · 1 33.3% · 0 5.3% (n=132)
- Alpha — median **255**; 255 94.7% · 200 2.3% · 170 0.8% (n=132)
- Dot enabled — **8.3%** (11/132 known)
- Outline enabled — **9.1%** (12/132 known)
- Dot and outline both disabled: **84.1%** (n=132, both fields known)

![crosshair_color.png](../figures/latest/crosshair_color.png)

- Color categories: Custom 43.8% · Cyan 37.5% · Yellow 12.5% · Green 6.2% (n=16)
- Custom RGB: **7/7** players with complete RGB (100.0%) · 6 unique exact colors · top **0,255,255** (28.6%)

## 5. Viewmodel

- `viewmodel_fov 68`: **90.4%** (n=125)
- Dominant offset: **X=2.5, Y=0, Z=-1.5**

## 6. Radar

![radar.png](../figures/latest/radar.png)

- Radar zoom — median **0.4**; 0.4 27.3% · 0.7 20.2% · 0.3 11.1% (n=99). Values are descriptive; no directional interpretation is applied.
- Radar centered enabled: 71.7% (n=120)

## 7. Extended segments

| Segment | Teams | Players | Median eDPI |
|---|---:|---:|---:|
| VRS ∩ HLTV Consensus | 27 | 134 | 800 |
| Ranked Union | 32 | 159 | 800 |
| Core + Watchlist | 33 | 164 | 800 |
| All tracked | 35 | 174 | 800 |

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
| Boost Player Contrast | 99 / 149 |
| Crosshair color | 16 / 149 |
| Crosshair style | 132 / 149 |
| Crosshair size | 132 / 149 |
| Crosshair gap | 132 / 149 |
| Crosshair thickness | 132 / 149 |
| Crosshair alpha | 132 / 149 |
| Crosshair dot | 132 / 149 |
| Crosshair outline | 132 / 149 |
| Viewmodel FOV | 125 / 149 |
| Radar zoom | 99 / 149 |
| Radar centered | 120 / 149 |
| Radar rotating | 0 / 149 |
| Monitor refresh rate | 0 / 149 |
| fps_max | 0 / 149 |

132/149 Core players currently have at least one usable settings field.
eDPI arithmetic QC flags 2/132 comparable observations; flags remain quality signals and do not overwrite source values.

## 10. Data & code

- Snapshot date: 2026-10-11
- Source: cs2settings
- Snapshot data: [`data/aggregate/2026-10.json`](../data/aggregate/2026-10.json)
- Project & methodology: [`README.md`](../README.md)
