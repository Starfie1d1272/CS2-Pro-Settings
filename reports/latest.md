# CS2 Professional Settings Snapshot — 2026-10

[中文版](./latest.zh-CN.md)

2026-10-20 · VRS Top 30 (2026-08-10) · 30 teams · 150 players · 134/150 settings · `vrs-core-v2`

## 1. Highlights

- **800 median eDPI** (n=134)
- **4:3** at 81.3%; **1280x960** at 66.4% (n=134 / 134)
- **Stretched scaling** at 86.6% (n=134)
- **1000 Hz polling** at 64.9%; 4000 Hz+ at 17.2% (n=134)
- **Dot + outline both off** for 87.3% (n=134)

## 2. Mouse

![mouse.png](../figures/latest/mouse.png)

- Median: **800** · Mean: **841.7** · n=134
- 600–1000 eDPI covers 68.7% of valid observations (92/134).
- Arithmetic QC: 132/134 consistent; **2 flagged** using max(2 eDPI, 1.0%) tolerance.
- DPI — 800: **49.3%** · 400: 46.3% · 1600+: 3.7% (n=134)
- Zoom sensitivity — median **1**; 1 76.7% · 1.1 5.3% · 0.8 3.8% (n=133)
- Polling — 1000: 64.9% · 2000: 17.9% · 4000: 14.9% · 8000 Hz: 2.2% (n=134)

## 3. Display

![display.png](../figures/latest/display.png)

- Aspect ratio — 4:3 81.3% · 16:9 9.7% · 5:4 6.0% (n=134)
- Resolution — 1280x960 66.4% · 1920x1080 10.4% · 1024x768 8.2% (n=134)
- Scaling mode — Stretched 86.6% · Native 8.2% · Black Bars 5.2% (n=134)
- Boost Player Contrast — enabled **83.8%** (83/99 known); disabled 16/99; missing/unknown 51/150.

## 4. Crosshair

![crosshair_geometry.png](../figures/latest/crosshair_geometry.png)

- Style codes — 4 96.3% · 5 1.5% · 3 0.7% (n=134); source-provided codes, with no mechanism interpretation.
- Size — median **2**; 2 59.7% · 3 14.9% · 4 14.2% (n=134)
- Gap — median **1**; 1 50.7% · 2 25.4% · 0 10.4% (n=134)
- Thickness — median **2**; 2 60.4% · 1 30.6% · 3 6.0% (n=134)
- Alpha — median **255**; 255 94.0% · 200 1.5% · 252 1.5% (n=134)
- Dot enabled — **8.2%** (11/134 known)
- Outline enabled — **5.2%** (7/134 known)
- Dot and outline both disabled: **87.3%** (n=134, both fields known)

![crosshair_color.png](../figures/latest/crosshair_color.png)

- Color categories: Cyan 50.0% · Yellow 50.0% (n=4)

## 5. Viewmodel

- `viewmodel_fov 68`: **90.5%** (n=127)
- Dominant offset: **X=2.5, Y=0, Z=-1.5**

## 6. Radar

![radar.png](../figures/latest/radar.png)

- Radar zoom — median **0.4**; 0.4 28.3% · 0.7 20.2% · 0.3 11.1% (n=99). Values are descriptive; no directional interpretation is applied.
- Radar centered enabled: 71.9% (n=121)

## 7. Extended segments

| Segment | Teams | Players | Median eDPI |
|---|---:|---:|---:|
| VRS ∩ HLTV Consensus | 27 | 135 | 800 |
| Ranked Union | 31 | 155 | 800 |
| Core + Watchlist | 33 | 165 | 800 |
| All tracked | 34 | 170 | 800 |

## 8. Changes since previous snapshot

- Previous snapshot: 2026-08-11
- Core cohort: 149 → 150 players
- Roster turnover: 0.0%
- Matched players: 148

- crosshair_minimal_share: 0.8045 -> 0.8731 (+6.9pp) [level 1]
- crosshair_dominant_color: Custom -> Cyan (changed) [level 2]

Matched panel (same players in both snapshots):
- dpi: 0/132 changed
- edpi: 0/132 changed
- resolution: 0/132 changed
- polling_rate: 0/132 changed

## 9. Coverage & quality

| Field | valid_n / cohort |
|---|---|
| eDPI | 134 / 150 |
| DPI | 134 / 150 |
| Zoom sensitivity | 133 / 150 |
| Mouse polling rate | 134 / 150 |
| Resolution | 134 / 150 |
| Aspect ratio | 134 / 150 |
| Scaling mode | 134 / 150 |
| Boost Player Contrast | 99 / 150 |
| Crosshair color | 4 / 150 |
| Crosshair style | 134 / 150 |
| Crosshair size | 134 / 150 |
| Crosshair gap | 134 / 150 |
| Crosshair thickness | 134 / 150 |
| Crosshair alpha | 134 / 150 |
| Crosshair dot | 134 / 150 |
| Crosshair outline | 134 / 150 |
| Viewmodel FOV | 127 / 150 |
| Radar zoom | 99 / 150 |
| Radar centered | 121 / 150 |
| Radar rotating | 0 / 150 |
| Monitor refresh rate | 0 / 150 |
| fps_max | 0 / 150 |

134/150 Core players currently have at least one usable settings field.
eDPI arithmetic QC flags 2/134 comparable observations; flags remain quality signals and do not overwrite source values.

## 10. Data & code

- Snapshot date: 2026-10-20
- Source: cs2settings
- Snapshot data: [`data/aggregate/2026-10.json`](../data/aggregate/2026-10.json)
- Project & methodology: [`README.md`](../README.md)
