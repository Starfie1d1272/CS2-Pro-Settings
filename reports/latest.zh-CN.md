# CS2 职业选手设置月度快照 — 2026-08

[English version](./latest.md)

2026-08-16 · VRS Top 30（2026-08-10）· 30 支战队 · 149 名选手 · 设置覆盖 132/149 · `vrs-core-v2`

## 1. 本期要点

- **eDPI 中位数 800**（n=132）
- **4:3** 占 81.8%；**1280x960** 占 68.9%（n=132 / 132）
- **Stretched 缩放**占 89.4%（n=132）
- **1000 Hz 回报率**占 62.1%；4000 Hz+ 占 18.2%（n=132）
- **Dot 与 outline 同时关闭**占 81.8%（n=132）

## 2. 鼠标

![mouse.png](../figures/latest/mouse.png)

- 中位数：**800** · 平均值：**843.7** · 有效样本：132
- 600–1000 eDPI 覆盖 69.7% 的有效样本（92/132）。
- 算术 QC：130/132 一致；按 max(2 eDPI, 1.0%) 容差标记 **2 项**。
- DPI — 800：**50.0%** · 400：45.5% · 1600+：3.8%（n=132）
- 开镜灵敏度 — 中位数 **1**；1 77.9% · 1.1 4.6% · 0.8 3.8%（n=131）
- 回报率 — 1000：62.1% · 2000：19.7% · 4000：15.9% · 8000 Hz：2.3%（n=132）

## 3. 显示

![display.png](../figures/latest/display.png)

- 宽高比 — 4:3 81.8% · 16:9 8.3% · 5:4 6.1%（n=132）
- 分辨率 — 1280x960 68.9% · 1920x1080 9.1% · 1024x768 6.8%（n=132）
- 缩放模式 — Stretched 89.4% · Native 6.8% · Black Bars 3.8%（n=132）
- Boost Player Contrast — 已开启 **84.0%** （84/100 项已知）；关闭 16/100；缺失/未知 49/149。

## 4. 准星

![crosshair_geometry.png](../figures/latest/crosshair_geometry.png)

- Style 原始代码 — 4 99.2% · 5 0.8%（n=132）；仅按来源值报告，不解释机制。
- Size — 中位数 **1**；1 56.1% · 2 18.2% · 1.5 6.8%（n=132）
- Gap — 中位数 **-4**；-4 42.4% · -3 23.5% · -2 6.1%（n=132）
- Thickness — 中位数 **1**；1 53.8% · 0 25.8% · 0.5 5.3%（n=132）
- Alpha — 中位数 **255**；255 78.0% · 200 20.5% · 175 0.8%（n=132）
- Dot 开启 — **9.8%**（13/132 项已知）
- Outline 开启 — **9.1%**（12/132 项已知）
- Dot 与 outline 同时关闭：**81.8%**（n=132，两字段均已知）

![crosshair_color.png](../figures/latest/crosshair_color.png)

- 颜色类别：Custom 37.4% · Cyan 32.1% · Green 22.9% · Yellow 7.6%（n=131）
- Custom RGB：**49/49** 名选手 RGB 三通道完整（100.0%）· 23 种精确颜色 · 最常用 **0,255,255**（16.3%）

## 5. Viewmodel

- `viewmodel_fov 68`：**91.1%**（n=124）
- 最常见三轴偏移：**X=2.5, Y=0, Z=-1.5**

## 6. Radar

![radar.png](../figures/latest/radar.png)

- Radar zoom — 中位数 **0.4**；0.4 28.6% · 0.7 19.4% · 0.3 11.2%（n=98）。仅报告数值分布，不作方向性解释。
- Radar centered 开启：71.4%（n=119）

## 7. 扩展样本

| Segment | 战队 | 选手 | eDPI 中位数 |
|---|---:|---:|---:|
| VRS ∩ HLTV Consensus | 27 | 134 | 800 |
| Ranked Union | 32 | 158 | 800 |
| Core + Watchlist | 33 | 163 | 800 |
| All tracked | 35 | 172 | 800 |

## 8. 相比上期

- 上一期：2026-08-11
- Core cohort：149 → 149 名选手
- roster turnover：0.0%
- matched players：149

同选手 matched panel（两期均在样本中的选手）：
- dpi: 0/132 changed
- edpi: 0/132 changed
- resolution: 0/132 changed
- polling_rate: 0/132 changed

## 9. 覆盖与质量

| 字段 | valid_n / cohort |
|---|---|
| eDPI | 132 / 149 |
| DPI | 132 / 149 |
| 开镜灵敏度 | 131 / 149 |
| 鼠标回报率 | 132 / 149 |
| 分辨率 | 132 / 149 |
| 宽高比 | 132 / 149 |
| 缩放模式 | 132 / 149 |
| Boost Player Contrast | 100 / 149 |
| 准星颜色 | 131 / 149 |
| 准星 style | 132 / 149 |
| 准星 size | 132 / 149 |
| 准星 gap | 132 / 149 |
| 准星 thickness | 132 / 149 |
| 准星 alpha | 132 / 149 |
| 准星 dot | 132 / 149 |
| 准星 outline | 132 / 149 |
| Viewmodel FOV | 124 / 149 |
| Radar zoom | 98 / 149 |
| Radar centered | 119 / 149 |
| Radar rotating | 0 / 149 |
| 显示器刷新率 | 0 / 149 |
| fps_max | 0 / 149 |

当前 132/149 名 Core 选手至少有一项可用设置字段。
eDPI 算术 QC 在 132 项可比较记录中标记 2 项；标记仅作为质量信号，不覆盖来源值。

## 10. 数据与代码

- 数据日期：2026-08-16
- 数据来源：cs2settings
- 快照数据：[`data/aggregate/2026-08.json`](../data/aggregate/2026-08.json)
- 项目与方法：[`README.md`](../README.md)
