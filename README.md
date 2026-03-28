# CS2 Pro Settings 数据分析

这个仓库整理了 CS2 职业选手参数数据，包含采集、清洗、分析和图表输出。

适合两类使用场景：

- 快速查看职业参数分布和图表结果
- 复现完整数据处理流程

## 快速入口

只看结果：

1. 打开 `04_final_report.ipynb`
2. 运行 Run All

看完整流程：

1. `01_data_collection.ipynb`（网页采集）
2. `02_data_cleaning.ipynb`（数据清洗与特征工程）
3. `03_statistical_analysis.ipynb`（数据质检 + K-Means 聚类 + 相关性分析）
4. `04_final_report.ipynb`（20+ 高级图表可视化输出）

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
│   ├── cs2_pro_2026_Active_Master.csv   # 主数据（基础）
│   ├── cs2_pro_detailed_RAW.csv         # 细节原始数据
│   ├── cs2_pro_2026_Active_Final.csv    # 分析使用的最终表
│   └── archive/
│       ├── cs2_pro_2026_Active_Cleaned.csv   # 关键中间表（清洗后）
│       ├── cs2_pro_raw.csv                    # 关键中间表（列表页原始抓取）
│       └── legacy_experiments/                # 历史实验产物
├── figures/                             # 已导出图表
├── 01_data_collection.ipynb
├── 02_data_cleaning.ipynb
├── 03_statistical_analysis.ipynb
├── 04_final_report.ipynb
├── analysis.py
├── requirements.txt
└── environment.yml
```

## 数据保留策略

主目录长期保留：

- `data/cs2_pro_2026_Active_Master.csv`
- `data/cs2_pro_2026_Active_Final.csv`
- `data/cs2_pro_detailed_RAW.csv`

`data/archive/` 保留关键中间表：

- `data/archive/cs2_pro_2026_Active_Cleaned.csv`
- `data/archive/cs2_pro_raw.csv`

历史实验与测试文件统一放入：

- `data/archive/legacy_experiments/`

这样可以同时满足两个目标：

- 主流程复现路径简洁，文件不混乱
- 历史研究痕迹可追溯，不需要硬删除

## 输出示例

图表位于 `figures/`，例如：

- `figures/eDPI.png`
- `figures/FOV.png`
- `figures/Custom Color.png`

<p align="center">
  <img src="figures/Custom Color.png" alt="Custom RGB Crosshair" width="80%">
</p>

## 数据范围

- 主题：CS2 职业选手参数
- 时间：2026 年整理版本

## 后续整理计划

- 清理每个 Notebook 中重复 import 和重复清洗逻辑
- 固定每个 Notebook 的输入/输出数据文件，减少手动改路径

## License

MIT License