# CS2 职业选手设置月度快照 — 2026-09

[English version](./latest.md)

2026-09-27 · VRS Top 30（2026-08-10）· 30 支战队 · 148 名选手 · 设置覆盖 130/148 · `vrs-core-v2`

## 1. 本期要点

- **eDPI 中位数 800**（n=130）
- **4:3** 占 80.8%；**1280x960** 占 66.2%（n=130 / 130）
- **Stretched 缩放**占 87.7%（n=130）
- **1000 Hz 回报率**占 65.4%；4000 Hz+ 占 16.2%（n=130）
- **Dot 与 outline 同时关闭**占 83.1%（n=130）

## 2. 鼠标

![mouse.png](../figures/latest/mouse.png)

- 中位数：**800** · 平均值：**842.9** · 有效样本：130
- 600–1000 eDPI 覆盖 68.5% 的有效样本（89/130）。
- 算术 QC：128/130 一致；按 max(2 eDPI, 1.0%) 容差标记 **2 项**。
- DPI — 800：**51.5%** · 400：43.8% · 1600+：3.8%（n=130）
- 开镜灵敏度 — 中位数 **1**；1 79.1% · 1.1 5.4% · 1.2 3.1%（n=129）
- 回报率 — 1000：65.4% · 2000：18.5% · 4000：13.8% · 8000 Hz：2.3%（n=130）

## 3. 显示

![display.png](../figures/latest/display.png)

- 宽高比 — 4:3 80.8% · 16:9 9.2% · 5:4 6.2%（n=130）
- 分辨率 — 1280x960 66.2% · 1920x1080 10.0% · 1024x768 7.7%（n=130）
- 缩放模式 — Stretched 87.7% · Native 7.7% · Black Bars 4.6%（n=130）
- Boost Player Contrast — 已开启 **84.4%** （81/96 项已知）；关闭 15/96；缺失/未知 52/148。

## 4. 准星

![crosshair_geometry.png](../figures/latest/crosshair_geometry.png)

- Style 原始代码 — 4 95.4% · 0 3.8% · 5 0.8%（n=130）；仅按来源值报告，不解释机制。
- Size — 中位数 **1**；1 56.2% · 2 16.9% · 1.5 5.4%（n=130）
- Gap — 中位数 **-4**；-4 43.1% · -3 18.5% · -5 6.2%（n=130）
- Thickness — 中位数 **1**；1 46.9% · 0 26.2% · 0.5 6.9%（n=130）
- Alpha — 中位数 **255**；255 76.2% · 200 18.5% · 1 3.1%（n=130）
- Dot 开启 — **6.2%**（8/130 项已知）
- Outline 开启 — **12.3%**（16/130 项已知）
- Dot 与 outline 同时关闭：**83.1%**（n=130，两字段均已知）

![crosshair_color.png](../figures/latest/crosshair_color.png)

- 颜色类别：Custom 40.5% · Cyan 29.4% · Green 24.6% · Yellow 4.8% · Blue 0.8%（n=126）
- Custom RGB：**51/51** 名选手 RGB 三通道完整（100.0%）· 21 种精确颜色 · 最常用 **0,255,0**（27.5%）

## 5. Viewmodel

- `viewmodel_fov 68`：**90.2%**（n=122）
- 最常见三轴偏移：**X=2.5, Y=0, Z=-1.5**

## 6. Radar

![radar.png](../figures/latest/radar.png)

- Radar zoom — 中位数 **0.4**；0.4 27.6% · 0.7 20.4% · 0.3 11.2%（n=98）。仅报告数值分布，不作方向性解释。
- Radar centered 开启：72.7%（n=117）

## 7. 扩展样本

| Segment | 战队 | 选手 | eDPI 中位数 |
|---|---:|---:|---:|
| VRS ∩ HLTV Consensus | 27 | 133 | 800 |
| Ranked Union | 32 | 158 | 800 |
| Core + Watchlist | 33 | 162 | 800 |
| All tracked | 35 | 172 | 800 |

## 8. 相比上期

- 上一期：2026-08-11
- Core cohort：149 → 148 名选手
- roster turnover：0.0%
- matched players：148

同选手 matched panel（两期均在样本中的选手）：
- dpi: 0/130 changed
- edpi: 0/130 changed
- resolution: 0/130 changed
- polling_rate: 0/130 changed

## 9. 覆盖与质量

| 字段 | valid_n / cohort |
|---|---|
| eDPI | 130 / 148 |
| DPI | 130 / 148 |
| 开镜灵敏度 | 129 / 148 |
| 鼠标回报率 | 130 / 148 |
| 分辨率 | 130 / 148 |
| 宽高比 | 130 / 148 |
| 缩放模式 | 130 / 148 |
| Boost Player Contrast | 96 / 148 |
| 准星颜色 | 126 / 148 |
| 准星 style | 130 / 148 |
| 准星 size | 130 / 148 |
| 准星 gap | 130 / 148 |
| 准星 thickness | 130 / 148 |
| 准星 alpha | 130 / 148 |
| 准星 dot | 130 / 148 |
| 准星 outline | 130 / 148 |
| Viewmodel FOV | 122 / 148 |
| Radar zoom | 98 / 148 |
| Radar centered | 117 / 148 |
| Radar rotating | 0 / 148 |
| 显示器刷新率 | 0 / 148 |
| fps_max | 0 / 148 |

当前 130/148 名 Core 选手至少有一项可用设置字段。
eDPI 算术 QC 在 130 项可比较记录中标记 2 项；标记仅作为质量信号，不覆盖来源值。

## 10. 数据与代码

- 数据日期：2026-09-27
- 数据来源：cs2settings
- 快照数据：[`data/aggregate/2026-09.json`](../data/aggregate/2026-09.json)
- 项目与方法：[`README.md`](../README.md)
