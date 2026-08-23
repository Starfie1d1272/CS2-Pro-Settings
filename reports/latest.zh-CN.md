# CS2 职业选手设置月度快照 — 2026-08

[English version](./latest.md)

2026-08-23 · VRS Top 30（2026-08-10）· 30 支战队 · 147 名选手 · 设置覆盖 131/147 · `vrs-core-v2`

## 1. 本期要点

- **eDPI 中位数 800**（n=131）
- **4:3** 占 81.7%；**1280x960** 占 68.7%（n=131 / 131）
- **Stretched 缩放**占 89.3%（n=131）
- **1000 Hz 回报率**占 61.8%；4000 Hz+ 占 18.3%（n=131）
- **Dot 与 outline 同时关闭**占 83.2%（n=131）

## 2. 鼠标

![mouse.png](../figures/latest/mouse.png)

- 中位数：**800** · 平均值：**843.1** · 有效样本：131
- 600–1000 eDPI 覆盖 69.5% 的有效样本（91/131）。
- 算术 QC：129/131 一致；按 max(2 eDPI, 1.0%) 容差标记 **2 项**。
- DPI — 800：**50.4%** · 400：45.0% · 1600+：3.8%（n=131）
- 开镜灵敏度 — 中位数 **1**；1 78.5% · 1.1 4.6% · 0.8 3.8%（n=130）
- 回报率 — 1000：61.8% · 2000：19.8% · 4000：16.0% · 8000 Hz：2.3%（n=131）

## 3. 显示

![display.png](../figures/latest/display.png)

- 宽高比 — 4:3 81.7% · 16:9 8.4% · 5:4 6.1%（n=131）
- 分辨率 — 1280x960 68.7% · 1920x1080 9.2% · 1024x768 6.9%（n=131）
- 缩放模式 — Stretched 89.3% · Native 6.9% · Black Bars 3.8%（n=131）
- Boost Player Contrast — 已开启 **84.0%** （84/100 项已知）；关闭 16/100；缺失/未知 47/147。

## 4. 准星

![crosshair_geometry.png](../figures/latest/crosshair_geometry.png)

- Style 原始代码 — 4 99.2% · 5 0.8%（n=131）；仅按来源值报告，不解释机制。
- Size — 中位数 **1**；1 58.0% · 2 16.0% · 1.5 6.1%（n=131）
- Gap — 中位数 **-4**；-4 42.7% · -3 21.4% · -2 5.3%（n=131）
- Thickness — 中位数 **1**；1 53.4% · 0 26.7% · 0.5 5.3%（n=131）
- Alpha — 中位数 **255**；255 79.4% · 200 19.1% · 175 0.8%（n=131）
- Dot 开启 — **9.9%**（13/131 项已知）
- Outline 开启 — **7.6%**（10/131 项已知）
- Dot 与 outline 同时关闭：**83.2%**（n=131，两字段均已知）

![crosshair_color.png](../figures/latest/crosshair_color.png)

- 颜色类别：Custom 39.7% · Cyan 32.1% · Green 23.7% · Yellow 4.6%（n=131）
- Custom RGB：**52/52** 名选手 RGB 三通道完整（100.0%）· 21 种精确颜色 · 最常用 **255,255,255**（19.2%）

## 5. Viewmodel

- `viewmodel_fov 68`：**91.1%**（n=123）
- 最常见三轴偏移：**X=2.5, Y=0, Z=-1.5**

## 6. Radar

![radar.png](../figures/latest/radar.png)

- Radar zoom — 中位数 **0.4**；0.4 28.6% · 0.7 19.4% · 0.3 11.2%（n=98）。仅报告数值分布，不作方向性解释。
- Radar centered 开启：71.4%（n=119）

## 7. 扩展样本

| Segment | 战队 | 选手 | eDPI 中位数 |
|---|---:|---:|---:|
| VRS ∩ HLTV Consensus | 27 | 132 | 800 |
| Ranked Union | 32 | 156 | 800 |
| Core + Watchlist | 33 | 161 | 800 |
| All tracked | 35 | 170 | 800 |

## 8. 相比上期

- 上一期：2026-08-11
- Core cohort：149 → 147 名选手
- roster turnover：0.0%
- matched players：147

同选手 matched panel（两期均在样本中的选手）：
- dpi: 0/131 changed
- edpi: 0/131 changed
- resolution: 0/131 changed
- polling_rate: 0/131 changed

## 9. 覆盖与质量

| 字段 | valid_n / cohort |
|---|---|
| eDPI | 131 / 147 |
| DPI | 131 / 147 |
| 开镜灵敏度 | 130 / 147 |
| 鼠标回报率 | 131 / 147 |
| 分辨率 | 131 / 147 |
| 宽高比 | 131 / 147 |
| 缩放模式 | 131 / 147 |
| Boost Player Contrast | 100 / 147 |
| 准星颜色 | 131 / 147 |
| 准星 style | 131 / 147 |
| 准星 size | 131 / 147 |
| 准星 gap | 131 / 147 |
| 准星 thickness | 131 / 147 |
| 准星 alpha | 131 / 147 |
| 准星 dot | 131 / 147 |
| 准星 outline | 131 / 147 |
| Viewmodel FOV | 123 / 147 |
| Radar zoom | 98 / 147 |
| Radar centered | 119 / 147 |
| Radar rotating | 0 / 147 |
| 显示器刷新率 | 0 / 147 |
| fps_max | 0 / 147 |

当前 131/147 名 Core 选手至少有一项可用设置字段。
eDPI 算术 QC 在 131 项可比较记录中标记 2 项；标记仅作为质量信号，不覆盖来源值。

## 10. 数据与代码

- 数据日期：2026-08-23
- 数据来源：cs2settings
- 快照数据：[`data/aggregate/2026-08.json`](../data/aggregate/2026-08.json)
- 项目与方法：[`README.md`](../README.md)
