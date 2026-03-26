# 🎮 CS2 Pro Meta 2026: 职业圈硬核参数白皮书

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange.svg)
![Seaborn](https://img.shields.io/badge/Seaborn-Cyberpunk_Theme-green.svg)
![Data](https://img.shields.io/badge/Players-Top_184-red.svg)

> **你觉得打不到人是因为天赋不够？看完这 184 名 Top 30 现役职业选手的硬核数据，也许纯粹是因为你的参数没抄对！**

本项目是一个基于 2026 年 CS2 现役顶级职业选手（涵盖 Top 30 战队共计 184 名核心选手）底层外设与画质设定的硬核数据挖掘项目。从最基础的 eDPI 偏好，到极限持枪视角的 XYZ 偏移，再到准星 Custom RGB 的真实色号扒皮，用数据揭示现代 CS2 的最强 Meta。

---

## 📁 项目结构 (Project Structure)

```text
├── data/                            # 核心数据集
│   ├── cs2_pro_2026_Active_Master.csv  # 原始基础数据
│   ├── cs2_pro_detailed_RAW.csv        # 原始细节增强数据
│   └── cs2_pro_2026_Active_Final.csv   # 经过 ETL 清洗后的终极分析大表
├── figures/                         # 赛博朋克主题高清可视化图表 (PNG)
├── CS2_Pro_Scraper.ipynb            # Phase 1: 数据采集与爬虫逻辑
├── Phase2_Data_Cleaning.ipynb       # Phase 2: 数据 ETL 清洗与特征工程
├── final_analysis.ipynb             # Phase 3: 面向白皮书的核心图表渲染引擎
├── LICENSE                          # 开源协议
└── README.md                        # 项目说明文档
```

---

## 🛠️ 如何运行 (How to Run)

本项目重构并封装了自定义的 **CS2 Cyberpunk Theme Engine (赛博朋克绘图引擎)**，完美支持暗黑风格、去边框与高对比度文字描边渲染。

1. **克隆仓库**
   ```bash
   git clone https://github.com/Starfie1d1272/CS2-Pro-Settings.git
   cd CS2-PRO-SETTINGS
   ```
2. **安装依赖**
   ```bash
   pip install pandas numpy matplotlib seaborn
   ```
3. **渲染图表**
   直接在 Jupyter Notebook 中打开 `final_analysis.ipynb`，一键运行即可复现所有高清定制图表。

---

## 📌 e.g.：Custom 准星到底是什么颜色？


<p align="center">
  <img src="figures/Custom Color.png" alt="Custom RGB Crosshair" width="80%">
</p>


## 📜 协议 (License)
本项目采用 MIT 协议开源，欢迎各位硬核 CS2 玩家、自媒体与数据分析师 Fork 与讨论。