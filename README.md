# CS2 Pro Settings 数据分析

这个仓库整理了 CS2 职业选手参数数据，包含采集、清洗、分析和图表输出。

适合两类使用场景：

- 快速查看职业参数分布和图表结果
- 复现完整数据处理流程

## 快速入口

只看结果：

1. 打开 `03_final_report.ipynb`
2. 运行 Run All

看完整流程：

1. `01_data_collection.ipynb`（网页采集）
2. `02_data_cleaning.ipynb`（清洗 + 质检 + 特征增强，一站式输出 Final.csv）
3. `03_final_report.ipynb`（20+ 图表可视化输出）

## 环境与安装

方式 A（通用，pip）：

```bash
pip install -r requirements.txt
```

方式 B（Conda）：

```bash
conda env create -f environment.yml
conda activate cs2_data
```

然后启动：

```bash
jupyter notebook
```

## 仓库结构

```text
.
├── data/
│   ├── cs2_pro_2026_Active_Master.csv   # 清洗后主数据
│   ├── cs2_pro_detailed_RAW.csv         # 详情页原始抓取
│   ├── cs2_pro_2026_Active_Final.csv    # 增强后最终分析表
│   └── cs2_pro_raw.csv                  # 列表页原始抓取
├── figures/                             # 已导出图表 (20+ PN)
├── 01_data_collection.ipynb             # 网页爬取
├── 02_data_cleaning.ipynb               # 清洗 + 特征工程
├── 04_final_report.ipynb                # 图表渲染引擎
├── CS-Pro-Settings.md                   # 正式数据分析文章
├── requirements.txt
├── environment.yml
└── social/                              # 社交平台发布模板
```

## 数据范围

- 主题：CS2 职业选手参数
- 时间：2026 年整理版本

## License

MIT License