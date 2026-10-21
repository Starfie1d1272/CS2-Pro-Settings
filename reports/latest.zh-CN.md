# CS2 职业选手设置月度快照 — 2026-10

[English version](./latest.md)

2026-10-21 · VRS Top 30（2026-08-10）· 30 支战队 · 151 名选手 · 设置覆盖 135/151 · `vrs-core-v2`

## 1. 本期要点

- **eDPI 中位数 800**（n=135）
- **4:3** 占 81.5%；**1280x960** 占 66.7%（n=135 / 135）
- **Stretched 缩放**占 86.7%（n=135）
- **1000 Hz 回报率**占 65.2%；4000 Hz+ 占 17.0%（n=135）
- **Dot 与 outline 同时关闭**占 87.4%（n=135）

## 2. 鼠标

![mouse.png](../figures/latest/mouse.png)

- 中位数：**800** · 平均值：**846.2** · 有效样本：135
- 600–1000 eDPI 覆盖 68.1% 的有效样本（92/135）。
- 算术 QC：133/135 一致；按 max(2 eDPI, 1.0%) 容差标记 **2 项**。
- DPI — 800：**48.9%** · 400：45.9% · 1600+：4.4%（n=135）
- 开镜灵敏度 — 中位数 **1**；1 76.9% · 1.1 5.2% · 0.8 3.7%（n=134）
- 回报率 — 1000：65.2% · 2000：17.8% · 4000：14.8% · 8000 Hz：2.2%（n=135）

## 3. 显示

![display.png](../figures/latest/display.png)

- 宽高比 — 4:3 81.5% · 16:9 9.6% · 5:4 5.9%（n=135）
- 分辨率 — 1280x960 66.7% · 1920x1080 10.4% · 1024x768 8.1%（n=135）
- 缩放模式 — Stretched 86.7% · Native 8.1% · Black Bars 5.2%（n=135）
- Boost Player Contrast — 已开启 **84.0%** （84/100 项已知）；关闭 16/100；缺失/未知 51/151。

## 4. 准星

![crosshair_geometry.png](../figures/latest/crosshair_geometry.png)

- Style 原始代码 — 4 95.6% · 5 1.5% · 8 1.5%（n=135）；仅按来源值报告，不解释机制。
- Size — 中位数 **2**；2 60.7% · 3 14.1% · 4 13.3%（n=135）
- Gap — 中位数 **1**；1 50.4% · 2 25.2% · 0 11.1%（n=135）
- Thickness — 中位数 **2**；2 60.0% · 1 31.1% · 3 5.9%（n=135）
- Alpha — 中位数 **255**；255 94.1% · 200 1.5% · 252 1.5%（n=135）
- Dot 开启 — **8.2%**（11/135 项已知）
- Outline 开启 — **5.2%**（7/135 项已知）
- Dot 与 outline 同时关闭：**87.4%**（n=135，两字段均已知）

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
| VRS ∩ HLTV Consensus | 27 | 136 | 800 |
| Ranked Union | 31 | 156 | 800 |
| Core + Watchlist | 33 | 166 | 800 |
| All tracked | 34 | 171 | 800 |

## 8. 相比上期

- 上一期：2026-08-11
- Core cohort：149 → 151 名选手
- roster turnover：0.0%
- matched players：150

- crosshair_minimal_share: 0.8045 -> 0.8741 (+7.0pp) [level 1]
- crosshair_dominant_color: Custom -> Cyan (changed) [level 2]

同选手 matched panel（两期均在样本中的选手）：
- dpi: 0/134 changed
- edpi: 0/134 changed
- resolution: 0/134 changed
- polling_rate: 0/134 changed

## 9. 覆盖与质量

| 字段 | valid_n / cohort |
|---|---|
| eDPI | 135 / 151 |
| DPI | 135 / 151 |
| 开镜灵敏度 | 134 / 151 |
| 鼠标回报率 | 135 / 151 |
| 分辨率 | 135 / 151 |
| 宽高比 | 135 / 151 |
| 缩放模式 | 135 / 151 |
| Boost Player Contrast | 100 / 151 |
| 准星颜色 | 4 / 151 |
| 准星 style | 135 / 151 |
| 准星 size | 135 / 151 |
| 准星 gap | 135 / 151 |
| 准星 thickness | 135 / 151 |
| 准星 alpha | 135 / 151 |
| 准星 dot | 135 / 151 |
| 准星 outline | 135 / 151 |
| Viewmodel FOV | 128 / 151 |
| Radar zoom | 100 / 151 |
| Radar centered | 122 / 151 |
| Radar rotating | 0 / 151 |
| 显示器刷新率 | 0 / 151 |
| fps_max | 0 / 151 |

当前 135/151 名 Core 选手至少有一项可用设置字段。
eDPI 算术 QC 在 135 项可比较记录中标记 2 项；标记仅作为质量信号，不覆盖来源值。

## 10. 数据与代码

- 数据日期：2026-10-21
- 数据来源：cs2settings
- 快照数据：[`data/aggregate/2026-10.json`](../data/aggregate/2026-10.json)
- 项目与方法：[`README.md`](../README.md)
