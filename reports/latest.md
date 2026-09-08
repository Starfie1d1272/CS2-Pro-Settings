# CS2 Professional Settings Snapshot — 2026-09

[中文版](./latest.zh-CN.md)

2026-09-08 · VRS Top 30 (2026-08-10) · 30 teams · 146 players · 127/146 settings · `vrs-core-v2`

## 1. Highlights

- **800 median eDPI** (n=127)
- **4:3** at 81.9%; **1280x960** at 68.5% (n=127 / 127)
- **Stretched scaling** at 88.2% (n=127)
- **1000 Hz polling** at 64.6%; 4000 Hz+ at 17.3% (n=127)
- **Dot + outline both off** for 81.9% (n=127)

## 2. Mouse

![mouse.png](../figures/latest/mouse.png)

- Median: **800** · Mean: **841.5** · n=127
- 600–1000 eDPI covers 70.1% of valid observations (89/127).
- Arithmetic QC: 126/127 consistent; **1 flagged** using max(2 eDPI, 1.0%) tolerance.
- DPI — 800: **51.2%** · 400: 44.1% · 1600+: 3.9% (n=127)
- Zoom sensitivity — median **1**; 1 77.8% · 1.1 5.6% · 0.8 4.0% (n=126)
- Polling — 1000: 64.6% · 2000: 18.1% · 4000: 15.0% · 8000 Hz: 2.4% (n=127)

## 3. Display

![display.png](../figures/latest/display.png)

- Aspect ratio — 4:3 81.9% · 16:9 8.7% · 5:4 5.5% (n=127)
- Resolution — 1280x960 68.5% · 1920x1080 9.4% · 1024x768 7.1% (n=127)
- Scaling mode — Stretched 88.2% · Native 7.1% · Black Bars 4.7% (n=127)
- Boost Player Contrast — enabled **83.2%** (79/95 known); disabled 16/95; missing/unknown 51/146.

## 4. Crosshair

![crosshair_geometry.png](../figures/latest/crosshair_geometry.png)

- Style codes — 4 99.2% · 5 0.8% (n=127); source-provided codes, with no mechanism interpretation.
- Size — median **1**; 1 52.0% · 2 22.8% · 1.5 7.1% (n=127)
- Gap — median **-4**; -4 45.7% · -3 24.4% · -2 5.5% (n=127)
- Thickness — median **1**; 1 52.0% · 0 31.5% · 0.5 3.9% (n=127)
- Alpha — median **255**; 255 91.3% · 200 5.5% · 250 1.6% (n=127)
- Dot enabled — **9.4%** (12/127 known)
- Outline enabled — **10.2%** (13/127 known)
- Dot and outline both disabled: **81.9%** (n=127, both fields known)

![crosshair_color.png](../figures/latest/crosshair_color.png)

- Color categories: Green 35.4% · Custom 33.1% · Cyan 26.8% · Yellow 4.7% (n=127)
- Custom RGB: **42/42** players with complete RGB (100.0%) · 18 unique exact colors · top **255,255,255** (19.1%)

## 5. Viewmodel

- `viewmodel_fov 68`: **90.8%** (n=119)
- Dominant offset: **X=2.5, Y=0, Z=-1.5**

## 6. Radar

![radar.png](../figures/latest/radar.png)

- Radar zoom — median **0.4**; 0.4 28.7% · 0.7 19.1% · 0.3 11.7% (n=94). Values are descriptive; no directional interpretation is applied.
- Radar centered enabled: 70.4% (n=115)

## 7. Extended segments

| Segment | Teams | Players | Median eDPI |
|---|---:|---:|---:|
| VRS ∩ HLTV Consensus | 27 | 131 | 800 |
| Ranked Union | 32 | 155 | 800 |
| Core + Watchlist | 33 | 160 | 800 |
| All tracked | 35 | 169 | 800 |

## 8. Changes since previous snapshot

- Previous snapshot: 2026-08-11
- Core cohort: 149 → 146 players
- Roster turnover: 0.7%
- Matched players: 146

- crosshair_dominant_color: Custom -> Green (changed) [level 2]

Matched panel (same players in both snapshots):
- dpi: 0/127 changed
- edpi: 0/127 changed
- resolution: 0/127 changed
- polling_rate: 0/127 changed

## 9. Coverage & quality

| Field | valid_n / cohort |
|---|---|
| eDPI | 127 / 146 |
| DPI | 127 / 146 |
| Zoom sensitivity | 126 / 146 |
| Mouse polling rate | 127 / 146 |
| Resolution | 127 / 146 |
| Aspect ratio | 127 / 146 |
| Scaling mode | 127 / 146 |
| Boost Player Contrast | 95 / 146 |
| Crosshair color | 127 / 146 |
| Crosshair style | 127 / 146 |
| Crosshair size | 127 / 146 |
| Crosshair gap | 127 / 146 |
| Crosshair thickness | 127 / 146 |
| Crosshair alpha | 127 / 146 |
| Crosshair dot | 127 / 146 |
| Crosshair outline | 127 / 146 |
| Viewmodel FOV | 119 / 146 |
| Radar zoom | 94 / 146 |
| Radar centered | 115 / 146 |
| Radar rotating | 0 / 146 |
| Monitor refresh rate | 0 / 146 |
| fps_max | 0 / 146 |

127/146 Core players currently have at least one usable settings field.
eDPI arithmetic QC flags 1/127 comparable observations; flags remain quality signals and do not overwrite source values.

## 10. Data & code

- Snapshot date: 2026-09-08
- Source: cs2settings
- Snapshot data: [`data/aggregate/2026-09.json`](../data/aggregate/2026-09.json)
- Project & methodology: [`README.md`](../README.md)
