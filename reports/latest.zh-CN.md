# CS2 职业选手设置月度快照 — 2026-10

[English version](./latest.md)

2026-10-24 · VRS Top 30（2026-08-10）· 30 支战队 · 150 名选手 · 设置覆盖 134/150 · `vrs-core-v2`

## 1. 本期要点

- **eDPI 中位数 800**（n=134）
- **4:3** 占 82.1%；**1280x960** 占 67.2%（n=134 / 134）
- **Stretched 缩放**占 86.6%（n=134）
- **1000 Hz 回报率**占 65.7%；4000 Hz+ 占 16.4%（n=134）
- **Dot 与 outline 同时关闭**占 85.8%（n=134）

## 2. 鼠标

![mouse.png](../figures/latest/mouse.png)

- 中位数：**800** · 平均值：**846.5** · 有效样本：134
- 600–1000 eDPI 覆盖 67.9% 的有效样本（91/134）。
- 算术 QC：132/134 一致；按 max(2 eDPI, 1.0%) 容差标记 **2 项**。
- DPI — 800：**49.3%** · 400：45.5% · 1600+：4.5%（n=134）
- 开镜灵敏度 — 中位数 **1**；1 76.7% · 1.1 5.3% · 0.8 3.8%（n=133）
- 回报率 — 1000：65.7% · 2000：17.9% · 4000：14.2% · 8000 Hz：2.2%（n=134）

## 3. 显示

![display.png](../figures/latest/display.png)

- 宽高比 — 4:3 82.1% · 16:9 9.7% · 5:4 5.2%（n=134）
- 分辨率 — 1280x960 67.2% · 1920x1080 10.4% · 1024x768 8.2%（n=134）
- 缩放模式 — Stretched 86.6% · Native 8.2% · Black Bars 5.2%（n=134）
- Boost Player Contrast — 已开启 **84.0%** （84/100 项已知）；关闭 16/100；缺失/未知 50/150。

## 4. 准星

![crosshair_geometry.png](../figures/latest/crosshair_geometry.png)

- Style 原始代码 — 4 94.8% · 8 2.2% · 5 1.5%（n=134）；仅按来源值报告，不解释机制。
- Size — 中位数 **2**；2 60.4% · 3 14.2% · 4 13.4%（n=134）
- Gap — 中位数 **1**；1 49.3% · 2 24.6% · 0 12.7%（n=134）
- Thickness — 中位数 **2**；2 59.7% · 1 29.9% · 3 7.5%（n=134）
- Alpha — 中位数 **255**；255 94.8% · 200 1.5% · 170 0.7%（n=134）
- Dot 开启 — **9.0%**（12/134 项已知）
- Outline 开启 — **6.0%**（8/134 项已知）
- Dot 与 outline 同时关闭：**85.8%**（n=134，两字段均已知）

![crosshair_color.png](../figures/latest/crosshair_color.png)

- 颜色类别：Cyan 50.0% · Yellow 50.0%（n=4）

## 5. Viewmodel

- `viewmodel_fov 68`：**90.6%**（n=128）
- 最常见三轴偏移：**X=2.5, Y=0, Z=-1.5**

## 6. Radar

![radar.png](../figures/latest/radar.png)

- Radar zoom — 中位数 **0.4**；0.4 28.0% · 0.7 20.0% · 0.3 11.0%（n=100）。仅报告数值分布，不作方向性解释。
- Radar centered 开启：72.1%（n=122）

## 7. 扩展样本

| Segment | 战队 | 选手 | eDPI 中位数 |
|---|---:|---:|---:|
| VRS ∩ HLTV Consensus | 27 | 135 | 800 |
| Ranked Union | 31 | 155 | 800 |
| Core + Watchlist | 33 | 165 | 800 |
| All tracked | 34 | 170 | 800 |

## 8. 相比上期

- 上一期：2026-08-11
- Core cohort：149 → 150 名选手
- roster turnover：0.0%
- matched players：150

- crosshair_minimal_share: 0.8045 -> 0.8582 (+5.4pp) [level 1]
- crosshair_dominant_color: Custom -> Cyan (changed) [level 2]

同选手 matched panel（两期均在样本中的选手）：
- dpi: 0/134 changed
- edpi: 0/134 changed
- resolution: 0/134 changed
- polling_rate: 0/134 changed

## 9. 覆盖与质量

| 字段 | valid_n / cohort |
|---|---|
| eDPI | 134 / 150 |
| DPI | 134 / 150 |
| 开镜灵敏度 | 133 / 150 |
| 鼠标回报率 | 134 / 150 |
| 分辨率 | 134 / 150 |
| 宽高比 | 134 / 150 |
| 缩放模式 | 134 / 150 |
| Boost Player Contrast | 100 / 150 |
| 准星颜色 | 4 / 150 |
| 准星 style | 134 / 150 |
| 准星 size | 134 / 150 |
| 准星 gap | 134 / 150 |
| 准星 thickness | 134 / 150 |
| 准星 alpha | 134 / 150 |
| 准星 dot | 134 / 150 |
| 准星 outline | 134 / 150 |
| Viewmodel FOV | 128 / 150 |
| Radar zoom | 100 / 150 |
| Radar centered | 122 / 150 |
| Radar rotating | 0 / 150 |
| 显示器刷新率 | 0 / 150 |
| fps_max | 0 / 150 |

当前 134/150 名 Core 选手至少有一项可用设置字段。
eDPI 算术 QC 在 134 项可比较记录中标记 2 项；标记仅作为质量信号，不覆盖来源值。

## 10. 数据与代码

- 数据日期：2026-10-24
- 数据来源：cs2settings
- 快照数据：[`data/aggregate/2026-10.json`](../data/aggregate/2026-10.json)
- 项目与方法：[`README.md`](../README.md)
