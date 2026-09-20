# CS2 Professional Settings Snapshot — 2026-09

[中文版](./latest.zh-CN.md)

2026-09-20 · VRS Top 30 (2026-08-10) · 30 teams · 149 players · 130/149 settings · `vrs-core-v2`

## 1. Highlights

- **800 median eDPI** (n=130)
- **4:3** at 80.8%; **1280x960** at 66.2% (n=130 / 130)
- **Stretched scaling** at 87.7% (n=130)
- **1000 Hz polling** at 65.4%; 4000 Hz+ at 16.9% (n=130)
- **Dot + outline both off** for 83.1% (n=130)

## 2. Mouse

![mouse.png](../figures/latest/mouse.png)

- Median: **800** · Mean: **838.1** · n=130
- 600–1000 eDPI covers 68.5% of valid observations (89/130).
- Arithmetic QC: 128/130 consistent; **2 flagged** using max(2 eDPI, 1.0%) tolerance.
- DPI — 800: **51.5%** · 400: 43.8% · 1600+: 3.8% (n=130)
- Zoom sensitivity — median **1**; 1 78.3% · 1.1 5.4% · 0.9 3.1% (n=129)
- Polling — 1000: 65.4% · 2000: 17.7% · 4000: 14.6% · 8000 Hz: 2.3% (n=130)

## 3. Display

![display.png](../figures/latest/display.png)

- Aspect ratio — 4:3 80.8% · 16:9 9.2% · 5:4 6.2% (n=130)
- Resolution — 1280x960 66.2% · 1920x1080 10.0% · 1024x768 7.7% (n=130)
- Scaling mode — Stretched 87.7% · Native 7.7% · Black Bars 4.6% (n=130)
- Boost Player Contrast — enabled **83.5%** (81/97 known); disabled 16/97; missing/unknown 52/149.

## 4. Crosshair

![crosshair_geometry.png](../figures/latest/crosshair_geometry.png)

- Style codes — 4 99.2% · 5 0.8% (n=130); source-provided codes, with no mechanism interpretation.
- Size — median **1**; 1 61.5% · 2 16.9% · 1.5 6.2% (n=130)
- Gap — median **-4**; -4 43.1% · -3 18.5% · -5 10.0% (n=130)
- Thickness — median **1**; 1 53.8% · 0 24.6% · 0.5 4.6% (n=130)
- Alpha — median **255**; 255 75.4% · 200 23.1% · 175 0.8% (n=130)
- Dot enabled — **7.7%** (10/130 known)
- Outline enabled — **10.8%** (14/130 known)
- Dot and outline both disabled: **83.1%** (n=130, both fields known)

![crosshair_color.png](../figures/latest/crosshair_color.png)

- Color categories: Custom 36.9% · Cyan 36.2% · Green 20.8% · Yellow 5.4% · Blue 0.8% (n=130)
- Custom RGB: **48/48** players with complete RGB (100.0%) · 20 unique exact colors · top **0,255,0** (27.1%)

## 5. Viewmodel

- `viewmodel_fov 68`: **90.2%** (n=122)
- Dominant offset: **X=2.5, Y=0, Z=-1.5**

## 6. Radar

![radar.png](../figures/latest/radar.png)

- Radar zoom — median **0.4**; 0.4 28.6% · 0.7 20.4% · 0.3 11.2% (n=98). Values are descriptive; no directional interpretation is applied.
- Radar centered enabled: 72.7% (n=117)

## 7. Extended segments

| Segment | Teams | Players | Median eDPI |
|---|---:|---:|---:|
| VRS ∩ HLTV Consensus | 27 | 134 | 800 |
| Ranked Union | 32 | 160 | 800 |
| Core + Watchlist | 33 | 163 | 800 |
| All tracked | 35 | 174 | 800 |

## 8. Changes since previous snapshot

- Previous snapshot: 2026-08-11
- Core cohort: 149 → 149 players
- Roster turnover: 0.0%
- Matched players: 149

Matched panel (same players in both snapshots):
- dpi: 0/130 changed
- edpi: 0/130 changed
- resolution: 0/130 changed
- polling_rate: 0/130 changed

## 9. Coverage & quality

| Field | valid_n / cohort |
|---|---|
| eDPI | 130 / 149 |
| DPI | 130 / 149 |
| Zoom sensitivity | 129 / 149 |
| Mouse polling rate | 130 / 149 |
| Resolution | 130 / 149 |
| Aspect ratio | 130 / 149 |
| Scaling mode | 130 / 149 |
| Boost Player Contrast | 97 / 149 |
| Crosshair color | 130 / 149 |
| Crosshair style | 130 / 149 |
| Crosshair size | 130 / 149 |
| Crosshair gap | 130 / 149 |
| Crosshair thickness | 130 / 149 |
| Crosshair alpha | 130 / 149 |
| Crosshair dot | 130 / 149 |
| Crosshair outline | 130 / 149 |
| Viewmodel FOV | 122 / 149 |
| Radar zoom | 98 / 149 |
| Radar centered | 117 / 149 |
| Radar rotating | 0 / 149 |
| Monitor refresh rate | 0 / 149 |
| fps_max | 0 / 149 |

130/149 Core players currently have at least one usable settings field.
eDPI arithmetic QC flags 2/130 comparable observations; flags remain quality signals and do not overwrite source values.

## 10. Data & code

- Snapshot date: 2026-09-20
- Source: cs2settings
- Snapshot data: [`data/aggregate/2026-09.json`](../data/aggregate/2026-09.json)
- Project & methodology: [`README.md`](../README.md)
