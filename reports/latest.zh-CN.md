# CS2 职业选手设置月度快照 — 2026-09

[English version](./latest.md)

2026-09-08 · VRS Top 30（2026-08-10）· 30 支战队 · 146 名选手 · 设置覆盖 127/146 · `vrs-core-v2`

## 1. 本期要点

- **eDPI 中位数 800**（n=127）
- **4:3** 占 81.9%；**1280x960** 占 68.5%（n=127 / 127）
- **Stretched 缩放**占 88.2%（n=127）
- **1000 Hz 回报率**占 64.6%；4000 Hz+ 占 17.3%（n=127）
- **Dot 与 outline 同时关闭**占 81.9%（n=127）

## 2. 鼠标

![mouse.png](../figures/latest/mouse.png)

- 中位数：**800** · 平均值：**841.5** · 有效样本：127
- 600–1000 eDPI 覆盖 70.1% 的有效样本（89/127）。
- 算术 QC：126/127 一致；按 max(2 eDPI, 1.0%) 容差标记 **1 项**。
- DPI — 800：**51.2%** · 400：44.1% · 1600+：3.9%（n=127）
- 开镜灵敏度 — 中位数 **1**；1 77.8% · 1.1 5.6% · 0.8 4.0%（n=126）
- 回报率 — 1000：64.6% · 2000：18.1% · 4000：15.0% · 8000 Hz：2.4%（n=127）

## 3. 显示

![display.png](../figures/latest/display.png)

- 宽高比 — 4:3 81.9% · 16:9 8.7% · 5:4 5.5%（n=127）
- 分辨率 — 1280x960 68.5% · 1920x1080 9.4% · 1024x768 7.1%（n=127）
- 缩放模式 — Stretched 88.2% · Native 7.1% · Black Bars 4.7%（n=127）
- Boost Player Contrast — 已开启 **83.2%** （79/95 项已知）；关闭 16/95；缺失/未知 51/146。

## 4. 准星

![crosshair_geometry.png](../figures/latest/crosshair_geometry.png)

- Style 原始代码 — 4 99.2% · 5 0.8%（n=127）；仅按来源值报告，不解释机制。
- Size — 中位数 **1**；1 52.0% · 2 22.8% · 1.5 7.1%（n=127）
- Gap — 中位数 **-4**；-4 45.7% · -3 24.4% · -2 5.5%（n=127）
- Thickness — 中位数 **1**；1 52.0% · 0 31.5% · 0.5 3.9%（n=127）
- Alpha — 中位数 **255**；255 91.3% · 200 5.5% · 250 1.6%（n=127）
- Dot 开启 — **9.4%**（12/127 项已知）
- Outline 开启 — **10.2%**（13/127 项已知）
- Dot 与 outline 同时关闭：**81.9%**（n=127，两字段均已知）

![crosshair_color.png](../figures/latest/crosshair_color.png)

- 颜色类别：Green 35.4% · Custom 33.1% · Cyan 26.8% · Yellow 4.7%（n=127）
- Custom RGB：**42/42** 名选手 RGB 三通道完整（100.0%）· 18 种精确颜色 · 最常用 **255,255,255**（19.1%）

## 5. Viewmodel

- `viewmodel_fov 68`：**90.8%**（n=119）
- 最常见三轴偏移：**X=2.5, Y=0, Z=-1.5**

## 6. Radar

![radar.png](../figures/latest/radar.png)

- Radar zoom — 中位数 **0.4**；0.4 28.7% · 0.7 19.1% · 0.3 11.7%（n=94）。仅报告数值分布，不作方向性解释。
- Radar centered 开启：70.4%（n=115）

## 7. 扩展样本

| Segment | 战队 | 选手 | eDPI 中位数 |
|---|---:|---:|---:|
| VRS ∩ HLTV Consensus | 27 | 131 | 800 |
| Ranked Union | 32 | 155 | 800 |
| Core + Watchlist | 33 | 160 | 800 |
| All tracked | 35 | 169 | 800 |

## 8. 相比上期

- 上一期：2026-08-11
- Core cohort：149 → 146 名选手
- roster turnover：0.7%
- matched players：146

- crosshair_dominant_color: Custom -> Green (changed) [level 2]

同选手 matched panel（两期均在样本中的选手）：
- dpi: 0/127 changed
- edpi: 0/127 changed
- resolution: 0/127 changed
- polling_rate: 0/127 changed

## 9. 覆盖与质量

| 字段 | valid_n / cohort |
|---|---|
| eDPI | 127 / 146 |
| DPI | 127 / 146 |
| 开镜灵敏度 | 126 / 146 |
| 鼠标回报率 | 127 / 146 |
| 分辨率 | 127 / 146 |
| 宽高比 | 127 / 146 |
| 缩放模式 | 127 / 146 |
| Boost Player Contrast | 95 / 146 |
| 准星颜色 | 127 / 146 |
| 准星 style | 127 / 146 |
| 准星 size | 127 / 146 |
| 准星 gap | 127 / 146 |
| 准星 thickness | 127 / 146 |
| 准星 alpha | 127 / 146 |
| 准星 dot | 127 / 146 |
| 准星 outline | 127 / 146 |
| Viewmodel FOV | 119 / 146 |
| Radar zoom | 94 / 146 |
| Radar centered | 115 / 146 |
| Radar rotating | 0 / 146 |
| 显示器刷新率 | 0 / 146 |
| fps_max | 0 / 146 |

当前 127/146 名 Core 选手至少有一项可用设置字段。
eDPI 算术 QC 在 127 项可比较记录中标记 1 项；标记仅作为质量信号，不覆盖来源值。

## 10. 数据与代码

- 数据日期：2026-09-08
- 数据来源：cs2settings
- 快照数据：[`data/aggregate/2026-09.json`](../data/aggregate/2026-09.json)
- 项目与方法：[`README.md`](../README.md)
