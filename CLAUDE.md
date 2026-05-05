# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

CS2 职业选手参数数据挖掘项目。从 prosettings.net 爬取 Top 战队现役选手的外设/画质/准星设置，经过 ETL 清洗后生成赛博朋克主题的可视化图表。

主报告：`CS-Pro-Settings.md`（面向读者的数据分析文章）。
仓库说明：`README.md`（面向开发者的复现指南）。

## 数据管道 (4 阶段)

```
01_data_collection.ipynb         → Phase 1: 网页爬取，产出 data/cs2_pro_raw.csv, data/cs2_pro_detailed_RAW.csv
02_data_cleaning.ipynb           → Phase 2: ETL 清洗 + 特征工程，产出 data/cs2_pro_2026_Active_Final.csv
03_statistical_analysis.ipynb    → Phase 3: 统计质检 + KMeans 聚类 + 相关性热力图
04_final_report.ipynb            → Phase 4: 20+ 张可视化图表渲染，产出 figures/*.png
```

数据流：`cs2_pro_2026_Active_Master.csv` → 清洗/特征工程 → `cs2_pro_2026_Active_Final.csv`（终极分析大表）。

## 环境

```bash
# 方式 A: conda（推荐）
conda env create -f environment.yml
conda activate cs2_data

# 方式 B: pip
pip install -r requirements.txt

# 启动
jupyter notebook
```

已有 conda 环境 `cs2pro`，与 `environment.yml` 等效。运行脚本时使用：
```bash
/opt/homebrew/Caskroom/miniforge/base/envs/cs2pro/bin/python <script>
```

## 绘图引擎

所有图表统一使用暗黑赛博朋克主题 (`dark_background` + 自定义 rcParams)，封装在 `04_final_report.ipynb` 的 Cell 1 工厂函数中：
- `setup_cs2_theme()` — 初始化全局 rcParams
- `plot_cs2_bar()` — 柱状图（自动标注数值）
- `plot_cs2_pie()` — 饼图（<4% 不显示标签）
- `plot_cs2_hist()` — 直方图 + KDE + 统计线

## 数据清洗规则

1. 剔除 eDPI / Resolution 为空的空壳记录
2. 剔除选手名与队伍名完全一致的假人数据
3. 大小写去重（按 Player 小写保留第一条）
4. Brightness 字段需 strip `%` 后转数值
5. Refresh Rate 需正则提取数字部分 `r'(\d+)'`

## 报告数据校验

修改 `CS-Pro-Settings.md` 中的数据声明时，用以下命令交叉验证：

```bash
/opt/homebrew/Caskroom/miniforge/base/envs/cs2pro/bin/python -c "
import pandas as pd
df = pd.read_csv('data/cs2_pro_2026_Active_Final.csv', low_memory=False)
# 替换为需要验证的查询
"
```

关键数字速查：
- 总选手: 184, 战队: 39
- eDPI 中位数: 800
- 800 DPI: 51.6%, 400 DPI: 42.4%
- 1280x960: 126 人 (68.5%), 4:3: 78.3%
- 360Hz: 33.3%, 540Hz+: 28.4%
- FOV 68: 85.2%, X=2.5/Y=0/Z=-1.5 为黄金公式
- 亮度 93%: 82 人
- Dot+Outline 双关: 86.3%
- V-Sync: 100% 关闭, Reflex: 48.5% 开启
