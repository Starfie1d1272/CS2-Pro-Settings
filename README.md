# CS2 Pro Settings 数据分析

CS2 职业选手参数数据采集、清洗、分析与可视化。

## 阅读报告

👉 **[拒绝脑补，只看数据：198名CS2现役职业选手设置深度分析](./CS-Pro-Settings.md)**

## 快速开始

只看图表结果：

```bash
jupyter notebook
# 打开 03_final_report.ipynb → Run All
```

复现完整流程：

```bash
# 1. 爬取数据（约 33 分钟）
jupyter notebook 01_data_collection.ipynb

# 2. 清洗 + 特征工程 → Final.csv
jupyter notebook 02_data_cleaning.ipynb

# 3. 生成 22 张图表 → figures/
jupyter notebook 03_final_report.ipynb
```

## 环境

```bash
conda env create -f environment.yml   # 或 pip install -r requirements.txt
conda activate cs2_data
```

## 仓库结构

```text
├── data/                        # 原始与清洗后数据集
├── figures/                     # 22 张可视化图表
├── 01_data_collection.ipynb     # 网页爬取
├── 02_data_cleaning.ipynb       # 清洗 + 特征工程
├── 03_final_report.ipynb        # 图表渲染引擎
├── CS-Pro-Settings.md           # 正式数据分析文章
├── social/                      # 社交平台发布模板
├── requirements.txt
└── environment.yml
```

## 数据范围

- 来源：[prosettings.net/lists/cs2](https://prosettings.net/lists/cs2/)
- 采集：2026-05-05 | 耗时约 33 分钟
- 选手：HLTV Top 30（2026-05-04）+ 老牌豪门/赛区代表/明星选手队，**41 队 198 人**

## License

MIT
