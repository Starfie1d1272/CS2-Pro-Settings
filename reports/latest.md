# CS2 Professional Settings Snapshot — 2026-11

[中文版](./latest.zh-CN.md)

2026-11-22 · VRS Top 30 (2026-08-10) · 30 teams · 160 players · 135/160 settings · `vrs-core-v2`

## 1. Highlights

- **800 median eDPI** (n=135)
- **4:3** at 83.0%; **1280x960** at 68.1% (n=135 / 135)
- **Stretched scaling** at 85.9% (n=135)
- **1000 Hz polling** at 66.7%; 4000 Hz+ at 14.8% (n=135)
- **Dot + outline both off** for 88.1% (n=135)

## 2. Mouse

![mouse.png](../figures/latest/mouse.png)

- Median: **800** · Mean: **846.9** · n=135
- 600–1000 eDPI covers 68.1% of valid observations (92/135).
- Arithmetic QC: 133/135 consistent; **2 flagged** using max(2 eDPI, 1.0%) tolerance.
- DPI — 800: **50.4%** · 400: 44.4% · 1600+: 4.4% (n=135)
- Zoom sensitivity — median **1**; 1 76.9% · 1.1 5.2% · 0.8 3.7% (n=134)
- Polling — 1000: 66.7% · 2000: 18.5% · 4000: 12.6% · 8000 Hz: 2.2% (n=135)

## 3. Display

![display.png](../figures/latest/display.png)

- Aspect ratio — 4:3 83.0% · 16:9 9.6% · 5:4 5.2% (n=135)
- Resolution — 1280x960 68.1% · 1920x1080 10.4% · 1024x768 8.1% (n=135)
- Scaling mode — Stretched 85.9% · Native 8.1% · Black Bars 5.9% (n=135)
- Boost Player Contrast — enabled **84.3%** (86/102 known); disabled 16/102; missing/unknown 58/160.

## 4. Crosshair

![crosshair_geometry.png](../figures/latest/crosshair_geometry.png)

- Style codes — 4 98.5% · 5 0.7% · 9 0.7% (n=135); source-provided codes, with no mechanism interpretation.
- Size — median **2**; 2 58.5% · 3 17.8% · 4 14.8% (n=135)
- Gap — median **1**; 1 54.8% · 2 30.4% · 0 6.7% (n=135)
- Thickness — median **2**; 2 64.4% · 1 31.1% · 3 3.7% (n=135)
- Alpha — median **255**; 255 97.8% · 159 0.7% · 200 0.7% (n=135)
- Dot enabled — **6.7%** (9/135 known)
- Outline enabled — **5.9%** (8/135 known)
- Dot and outline both disabled: **88.1%** (n=135, both fields known)

## 5. Viewmodel

- `viewmodel_fov 68`: **89.9%** (n=129)
- Dominant offset: **X=2.5, Y=0, Z=-1.5**

## 6. Radar

![radar.png](../figures/latest/radar.png)

- Radar zoom — median **0.4**; 0.4 28.2% · 0.7 20.4% · 0.3 10.7% (n=103). Values are descriptive; no directional interpretation is applied.
- Radar centered enabled: 73.4% (n=124)

## 7. Extended segments

| Segment | Teams | Players | Median eDPI |
|---|---:|---:|---:|
| VRS ∩ HLTV Consensus | 27 | 145 | 800 |
| Ranked Union | 31 | 165 | 800 |
| Core + Watchlist | 33 | 175 | 800 |
| All tracked | 34 | 180 | 800 |

## 8. Changes since previous snapshot

- Previous snapshot: 2026-08-11
- Core cohort: 149 → 160 players
- Roster turnover: 0.0%
- Matched players: 160

- crosshair_minimal_share: 0.8045 -> 0.8815 (+7.7pp) [level 1]

Matched panel (same players in both snapshots):
- dpi: 0/135 changed
- edpi: 0/135 changed
- resolution: 0/135 changed
- polling_rate: 0/135 changed

## 9. Coverage & quality

| Field | valid_n / cohort |
|---|---|
| eDPI | 135 / 160 |
| DPI | 135 / 160 |
| Zoom sensitivity | 134 / 160 |
| Mouse polling rate | 135 / 160 |
| Resolution | 135 / 160 |
| Aspect ratio | 135 / 160 |
| Scaling mode | 135 / 160 |
| Boost Player Contrast | 102 / 160 |
| Crosshair color | 0 / 160 |
| Crosshair style | 135 / 160 |
| Crosshair size | 135 / 160 |
| Crosshair gap | 135 / 160 |
| Crosshair thickness | 135 / 160 |
| Crosshair alpha | 135 / 160 |
| Crosshair dot | 135 / 160 |
| Crosshair outline | 135 / 160 |
| Viewmodel FOV | 129 / 160 |
| Radar zoom | 103 / 160 |
| Radar centered | 124 / 160 |
| Radar rotating | 0 / 160 |
| Monitor refresh rate | 0 / 160 |
| fps_max | 0 / 160 |

135/160 Core players currently have at least one usable settings field.
eDPI arithmetic QC flags 2/135 comparable observations; flags remain quality signals and do not overwrite source values.

## 10. Data & code

- Snapshot date: 2026-11-22
- Source: cs2settings
- Snapshot data: [`data/aggregate/2026-11.json`](../data/aggregate/2026-11.json)
- Project & methodology: [`README.md`](../README.md)
