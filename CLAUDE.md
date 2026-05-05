# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

CS2 职业选手参数数据挖掘项目。从 prosettings.net 爬取 Top 战队现役选手的外设/画质/准星设置，经过 ETL 清洗后生成赛博朋克主题的可视化图表。

主报告：`CS-Pro-Settings.md`（面向读者的数据分析文章）。
仓库说明：`README.md`（面向开发者的复现指南）。

## 数据管道 (3 阶段)

```
01_data_collection.ipynb  → Phase 1: 网页爬取 → cs2_pro_raw.csv, cs2_pro_detailed_RAW.csv
02_data_cleaning.ipynb    → Phase 2: ETL 清洗 + 质检 + 特征增强 → cs2_pro_2026_Active_Final.csv
03_final_report.ipynb     → Phase 3: 23 张图表渲染（22 数据分析 + 1 AI 生成全览）→ figures/*.png
```

02 是唯一的清洗入口：
- Cell 1: 战队白名单（41队/64变体）+ 选手白名单（202人/216变体，含HLTV→prosettings别名）
- Cell 2: 数值化 + 质检去重 → Master.csv
- Cell 3: RAW特征合并（30+字段，含准星/视角/雷达） → Final.csv
- Cell 4: 就绪检查

03 Cell 0 包含跨平台中文字体自动检测（Windows → macOS → Linux fallback），无需手动配置。

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

所有图表统一使用暗黑赛博朋克主题 (`dark_background` + 自定义 rcParams)，封装在 `03_final_report.ipynb` 的 Cell 0 中：
- `setup_cs2_theme()` — 初始化全局 rcParams
- `bar()` — 柱状图（自动标注数值）
- `pie()` — 饼图
- `hist()` — 直方图 + KDE + 可选均值/中位数参考线
- `save()` — 封装 `plt.savefig()`，统一输出到 `figures/`，150dpi

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

关键数字速查（198人/41队, 数据截至2026-05-05）：
- eDPI 中位数: 800, 均值: 848
- 800 DPI: 53.5%, 400 DPI: 41.4%, >=1600: 3.5%
- 1280x960: 134人 (67.7%), 4:3: 78.1%
- 显示器: 360Hz 31.8%, 540Hz+ 31.8%
- FOV 68: 85.3%, X=2.5/Y=0/Z=-1.5 为黄金公式
- 亮度 93%: 87人, 100%: 18人, 130%: 23人
- Dot+Outline 双关: 81.8%
- 准星颜色: Custom 38.4%, Cyan 31.3%, Green 23.2%
- V-Sync: 100% 关闭, Reflex: 48.5% 开启
- 雷达旋转: 79.3%, 雷达居中: 72.2%
- 亮度默认值即为 93%, 并非选手精心选择
- 鼠标回报率: 1000Hz 62.6%, 4000Hz+ 18.2%

## 发布与社交平台

- 主报告 `CS-Pro-Settings.md` → GitHub README 引用
- `social/heybox-article.md` → 小黑盒（标题栏手动填，不支持 `` ` `` 和 H3/H4，图片拖入）
- `social/xiaohongshu.md` → 小红书 9 篇拆解（5 天发布计划）
- `social/wechat.md` / `social/bilibili.md` → 公众号/B站参考
- 公众号账号: Starfie1d（科技互联网+科学科普+旅游摄影）

## 已知缺口

- RAW 中有 Gamma、Digital Vibrance、Color Temperature 等显示器参数未提取到 02 pipeline
- CITATION.cff 已配置 GitHub 引用按钮，LICENSE 为 CC BY 4.0
