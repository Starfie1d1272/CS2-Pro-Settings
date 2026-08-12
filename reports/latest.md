# CS2 Professional Settings Snapshot — 2026-08

[中文版](./latest.zh-CN.md)

2026-08-11 · VRS Top 30 (2026-08-10) · 30 teams · 149 players · 133/149 settings · `vrs-core-v2` baseline

## 1. Highlights

- **800 median eDPI** (n=133)
- **4:3** at 82.0%; **1280x960** at 68.4% (n=133 / 133)
- **Stretched scaling** at 89.5% (n=133)
- **1000 Hz polling** at 62.4%; 4000 Hz+ at 18.0% (n=133)
- **Dot + outline both off** for 80.5% (n=133)

## 2. Mouse

![mouse.png](../figures/latest/mouse.png)

- Median: **800** · Mean: **844.3** · n=133
- 600–1000 eDPI covers 69.9% of valid observations (93/133).
- Arithmetic QC: 131/133 consistent; **2 flagged** using max(2 eDPI, 1.0%) tolerance.
- DPI — 800: **50.4%** · 400: 45.1% · 1600+: 3.8% (n=133)
- Zoom sensitivity — median **1**; 1 78.0% · 1.1 4.5% · 0.8 3.8% (n=132)
- Polling — 1000: 62.4% · 2000: 19.5% · 4000: 15.8% · 8000 Hz: 2.3% (n=133)

## 3. Display

![display.png](../figures/latest/display.png)

- Aspect ratio — 4:3 82.0% · 16:9 8.3% · 5:4 6.0% (n=133)
- Resolution — 1280x960 68.4% · 1920x1080 9.0% · 1024x768 7.5% (n=133)
- Scaling mode — Stretched 89.5% · Native 6.8% · Black Bars 3.8% (n=133)
- Boost Player Contrast — enabled **84.2%** (85/101 known); disabled 16/101; missing/unknown 48/149.

## 4. Crosshair

![crosshair_geometry.png](../figures/latest/crosshair_geometry.png)

- Style codes — 4 99.2% · 5 0.8% (n=133); source-provided codes, with no mechanism interpretation.
- Size — median **1**; 1 48.9% · 2 19.5% · 1.5 9.8% (n=133)
- Gap — median **-4**; -4 39.8% · -3 22.6% · -2 6.0% (n=133)
- Thickness — median **1**; 1 49.6% · 0 32.3% · 0.5 5.3% (n=133)
- Alpha — median **255**; 255 85.0% · 200 13.5% · 235 0.8% (n=133)
- Dot enabled — **9.8%** (13/133 known)
- Outline enabled — **12.8%** (17/133 known)
- Dot and outline both disabled: **80.5%** (n=133, both fields known)

![crosshair_color.png](../figures/latest/crosshair_color.png)

- Color categories: Custom 45.1% · Cyan 26.3% · Green 22.6% · Yellow 6.0% (n=133)
- Custom RGB: **60/60** players with complete RGB (100.0%) · 26 unique exact colors · top **255,255,255** (25.0%)

## 5. Viewmodel

- `viewmodel_fov 68`: **91.2%** (n=125)
- Dominant offset: **X=2.5, Y=0, Z=-1.5**

## 6. Radar

![radar.png](../figures/latest/radar.png)

- Radar zoom — median **0.4**; 0.4 29.3% · 0.7 20.2% · 0.3 10.1% (n=99). Values are descriptive; no directional interpretation is applied.
- Radar centered enabled: 71.7% (n=120)

## 7. Extended segments

| Segment | Teams | Players | Median eDPI |
|---|---:|---:|---:|
| VRS ∩ HLTV Consensus | 27 | 134 | 800 |
| Ranked Union | 32 | 158 | 800 |
| Core + Watchlist | 33 | 163 | 800 |
| All tracked | 35 | 172 | 800 |

## 8. Coverage & quality

| Field | valid_n / cohort |
|---|---|
| eDPI | 133 / 149 |
| DPI | 133 / 149 |
| Zoom sensitivity | 132 / 149 |
| Mouse polling rate | 133 / 149 |
| Resolution | 133 / 149 |
| Aspect ratio | 133 / 149 |
| Scaling mode | 133 / 149 |
| Boost Player Contrast | 101 / 149 |
| Crosshair color | 133 / 149 |
| Crosshair style | 133 / 149 |
| Crosshair size | 133 / 149 |
| Crosshair gap | 133 / 149 |
| Crosshair thickness | 133 / 149 |
| Crosshair alpha | 133 / 149 |
| Crosshair dot | 133 / 149 |
| Crosshair outline | 133 / 149 |
| Viewmodel FOV | 125 / 149 |
| Radar zoom | 99 / 149 |
| Radar centered | 120 / 149 |
| Radar rotating | 0 / 149 |
| Monitor refresh rate | 0 / 149 |
| fps_max | 0 / 149 |

133/149 Core players currently have at least one usable settings field.
eDPI arithmetic QC flags 2/133 comparable observations; flags remain quality signals and do not overwrite source values.

## 9. Data & code

- Snapshot date: 2026-08-11
- Source: cs2settings
- Snapshot data: [`data/aggregate/2026-08.json`](../data/aggregate/2026-08.json)
- Project & methodology: [`README.md`](../README.md)
