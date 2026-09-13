# CS2 Professional Settings Snapshot — 2026-09

[中文版](./latest.zh-CN.md)

2026-09-13 · VRS Top 30 (2026-08-10) · 30 teams · 150 players · 130/150 settings · `vrs-core-v2`

## 1. Highlights

- **800 median eDPI** (n=130)
- **4:3** at 81.5%; **1280x960** at 66.9% (n=130 / 130)
- **Stretched scaling** at 88.5% (n=130)
- **1000 Hz polling** at 64.6%; 4000 Hz+ at 16.9% (n=130)
- **Dot + outline both off** for 83.1% (n=130)

## 2. Mouse

![mouse.png](../figures/latest/mouse.png)

- Median: **800** · Mean: **839.6** · n=130
- 600–1000 eDPI covers 69.2% of valid observations (90/130).
- Arithmetic QC: 128/130 consistent; **2 flagged** using max(2 eDPI, 1.0%) tolerance.
- DPI — 800: **51.5%** · 400: 43.8% · 1600+: 3.8% (n=130)
- Zoom sensitivity — median **1**; 1 78.3% · 1.1 5.4% · 0.8 3.1% (n=129)
- Polling — 1000: 64.6% · 2000: 18.5% · 4000: 14.6% · 8000 Hz: 2.3% (n=130)

## 3. Display

![display.png](../figures/latest/display.png)

- Aspect ratio — 4:3 81.5% · 16:9 8.5% · 5:4 6.2% (n=130)
- Resolution — 1280x960 66.9% · 1920x1080 9.2% · 1024x768 7.7% (n=130)
- Scaling mode — Stretched 88.5% · Native 6.9% · Black Bars 4.6% (n=130)
- Boost Player Contrast — enabled **83.7%** (82/98 known); disabled 16/98; missing/unknown 52/150.

## 4. Crosshair

![crosshair_geometry.png](../figures/latest/crosshair_geometry.png)

- Style codes — 4 99.2% · 5 0.8% (n=130); source-provided codes, with no mechanism interpretation.
- Size — median **1**; 1 61.5% · 2 16.9% · 1.5 5.4% (n=130)
- Gap — median **-4**; -4 45.4% · -3 18.5% · -5 9.2% (n=130)
- Thickness — median **1**; 1 53.1% · 0 24.6% · 0.5 4.6% (n=130)
- Alpha — median **255**; 255 75.4% · 200 23.1% · 175 0.8% (n=130)
- Dot enabled — **6.2%** (8/130 known)
- Outline enabled — **12.3%** (16/130 known)
- Dot and outline both disabled: **83.1%** (n=130, both fields known)

![crosshair_color.png](../figures/latest/crosshair_color.png)

- Color categories: Custom 39.2% · Cyan 33.1% · Green 22.3% · Yellow 5.4% (n=130)
- Custom RGB: **51/51** players with complete RGB (100.0%) · 20 unique exact colors · top **0,255,0** (23.5%)

## 5. Viewmodel

- `viewmodel_fov 68`: **90.2%** (n=122)
- Dominant offset: **X=2.5, Y=0, Z=-1.5**

## 6. Radar

![radar.png](../figures/latest/radar.png)

- Radar zoom — median **0.4**; 0.4 28.9% · 0.7 20.6% · 0.3 11.3% (n=97). Values are descriptive; no directional interpretation is applied.
- Radar centered enabled: 71.8% (n=117)

## 7. Extended segments

| Segment | Teams | Players | Median eDPI |
|---|---:|---:|---:|
| VRS ∩ HLTV Consensus | 27 | 135 | 800 |
| Ranked Union | 32 | 160 | 800 |
| Core + Watchlist | 33 | 164 | 800 |
| All tracked | 35 | 174 | 800 |

## 8. Changes since previous snapshot

- Previous snapshot: 2026-08-11
- Core cohort: 149 → 150 players
- Roster turnover: 1.3%
- Matched players: 150

Matched panel (same players in both snapshots):
- dpi: 0/130 changed
- edpi: 0/130 changed
- resolution: 0/130 changed
- polling_rate: 0/130 changed

## 9. Coverage & quality

| Field | valid_n / cohort |
|---|---|
| eDPI | 130 / 150 |
| DPI | 130 / 150 |
| Zoom sensitivity | 129 / 150 |
| Mouse polling rate | 130 / 150 |
| Resolution | 130 / 150 |
| Aspect ratio | 130 / 150 |
| Scaling mode | 130 / 150 |
| Boost Player Contrast | 98 / 150 |
| Crosshair color | 130 / 150 |
| Crosshair style | 130 / 150 |
| Crosshair size | 130 / 150 |
| Crosshair gap | 130 / 150 |
| Crosshair thickness | 130 / 150 |
| Crosshair alpha | 130 / 150 |
| Crosshair dot | 130 / 150 |
| Crosshair outline | 130 / 150 |
| Viewmodel FOV | 122 / 150 |
| Radar zoom | 97 / 150 |
| Radar centered | 117 / 150 |
| Radar rotating | 0 / 150 |
| Monitor refresh rate | 0 / 150 |
| fps_max | 0 / 150 |

130/150 Core players currently have at least one usable settings field.
eDPI arithmetic QC flags 2/130 comparable observations; flags remain quality signals and do not overwrite source values.

## 10. Data & code

- Snapshot date: 2026-09-13
- Source: cs2settings
- Snapshot data: [`data/aggregate/2026-09.json`](../data/aggregate/2026-09.json)
- Project & methodology: [`README.md`](../README.md)
