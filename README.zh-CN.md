# CS2 职业选手设置追踪

[English](./README.md) | 简体中文

**顶级职业选手究竟都在怎么设置 CS2？这些"职业标准答案"又会随着版本、硬件和选手更替发生什么变化？**

CS2 Pro Settings Tracker 是一个面向职业赛场的长期设置数据追踪项目。

它不只是再爬一张职业选手设置表，而是以当前 VRS 世界 Top 30 为核心样本，持续追踪战队阵容、稳定玩家身份和各项设置，并按月保存可复现快照，从而区分：

- 职业赛场整体偏好真的发生了变化；
- 只是 Top 战队换了一批选手；
- 还是同一名职业选手真的修改了设置。

## 最新一期

**2026-08-11 · VRS Top 30 · 30 支战队 · 149 名选手** —— 第一份正式接受的 `vrs-core-v2` baseline。

- 133/149 名选手有可用设置数据（89.3%）
- 中位 eDPI 800
- 400 + 800 DPI 合计 95.5%
- 4:3 占 82.0%
- 1280×960 占 68.4%
- 1000 Hz 占 62.4%
- 4000 Hz+ 占 18.0%
- viewmodel_fov 68 占 91.2%

从当前快照来看，800 eDPI、4:3、1280×960 和 FOV 68 依然构成非常稳定的职业赛场主流画像。

→ [最新中文报告](./reports/latest.zh-CN.md) · [English report](./reports/latest.md) · [月度存档](./reports/2026-08.zh-CN.md)

## 为什么要做这个项目？

普通职业设置网站适合回答："某个选手现在用什么？"

本项目要回答的是另一个问题：**整个职业赛场的设置偏好如何随时间变化？**

- 800 DPI 是否继续替代 400 DPI？
- 4:3 会不会真正退出职业赛场？
- 4K / 8K polling rate 会不会成为新标准？
- 数据变化来自 roster change，还是同一名选手真的改设置？
- 同一选手几个月后修改了哪些参数？

一次性静态表不能回答这些问题。所以项目从 2026-05 的一次数据分析，演化成了现在的长期追踪管线。

## 从一篇分析，到长期追踪

第一期社区文章（小黑盒，2026-05-05 发布）统计了 41 支战队、198 名选手，收到了大量反馈。人工记录的互动快照（截至 2026-08-11；**不**自动更新）：

- 2852 赞
- 4408 收藏
- 402 评论

第一期反馈促使项目从一次性分析继续演化成现在的自动化追踪。记录：[`social/2026-05/publication.md`](./social/2026-05/publication.md)

## 这个项目有什么不同？

### 稳定玩家身份
选手以 SteamID（`steam:<id>`）为永久身份，绝不用裸昵称，因此同一名选手可以跨时间、跨来源被持续追踪。

### 阵容变化感知
Core 样本是已接受的 VRS Top 30。阵容按战队、按稳定身份逐期追踪，roster 更替与设置变化分开处理。

### 同选手纵向追踪
同一名选手出现在两个快照中时，其字段会被直接比较。`missing → value` 与 `value → missing` 视为数据完整性变化，而不是选手修改设置。

### 可复现月度快照
每个已接受的月份都会存档为机器可读 aggregate（`data/aggregate/`）加确定性双语报告（`reports/latest.md` / `reports/YYYY-MM.md`，英文 + 中文）。

### 自动化，但不自动合并
采集、漂移检测和候选 PR 全部自动化；没有任何内容会被自动合并。报告由确定性代码生成，不调用 LLM 编造结论。

## 工作流程

```
VRS Top 30（已接受的排名快照）
  ↓
当前阵容（按战队、稳定 ID）
  ↓
稳定 SteamID 身份
  ↓
设置采集（普通 HTTP，fail closed）
  ↓
归一化 / 冲突仲裁（冲突浮出，绝不静默覆盖）
  ↓
月度快照（已接受 aggregate + 双语报告）
  ↓
当前 cohort + 同选手 matched 分析
  ↓
报告 / 社区文章
```

## Cohort 模型

- **Core（主样本）**：已接受的 Valve VRS 世界 Top 30 快照 —— 手动导入，绝不爬取。
- **Reference**：已接受的 HLTV 世界排名 Top 30（敏感性参照）。
- **扩展 segment**：consensus（VRS ∩ HLTV）、ranked union（VRS ∪ HLTV）、Core + Watchlist、all tracked —— 只有存在真实数值时才在报告中展示。
- **Series 兼容性**：`vrs-core-v2`（自 2026-08 起）是当前纵向系列。2026-05 历史快照（`legacy-top30-plus-selected-v1`，41 支战队 / 198 名选手）仅作历史参照，**不**作为可直接比较的纵向 baseline。
- 排名真实性与设置源覆盖相互独立：某个源的映射无法解析只会降低采集覆盖，不会否定排名。

## 自动化与审阅门禁

- **CI**：离线 pytest（DeprecationWarning 视为错误）+ 离线 fixture 端到端 + 确定性输出检查，每个 PR 都会跑。
- **Daily**：source health → scope → roster → settings → metrics → drift；issue 去重；仅在 Level 2 且 scope / roster 稳定时创建候选 PR。
- **Weekly**：质量 / 维护检查、排名新鲜度、月度快照到期检查。
- **Monthly**：`data/aggregate/YYYY-MM.json` 缺失或过期时创建候选，并同步四个报告文件（`latest.md`、`latest.zh-CN.md`、`YYYY-MM.md`、`YYYY-MM.zh-CN.md`）——latest 永远不会比同月存档更新。
- 没有任何自动合并；issue 与候选 PR 全部去重。

## 漂移规则

`config/conclusions.yaml` 中的确定性规则（无 LLM）：Level 1 = 份额变化 ≥ 5 个百分点（或 eDPI 中位数变化 ≥ 50）；Level 2 = 主导类别翻转。当 Core roster turnover ≥ 15% 或 Core scope 变化时，整体 headline Level 2 会被抑制，等待人工审阅。这些是**运维通知阈值，不是统计显著性**。

## 数据源政策

| Source | 阵容发现 | 选手设置 | 稳定身份 | 定时采集 | 本地审阅 |
|---|---|---|---|---|---|
| cs2settings.com | yes | yes | yes | yes | yes |
| prosettings.net | no | yes | yes（数字 /profiles/） | **no** | yes |
| proconfig.net | no | yes | yes | no（disabled） | opt-in |

逐源审计：`docs/source-audit/`。仅使用普通 HTTP；无反爬绕过、验证码破解、代理轮换或浏览器自动化。第三方逐行数据不重新分发（`DATA_PROVENANCE.md`）。

## 本地复现

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -v                          # 离线测试
python -m cs2_pro_settings update --offline  # fixture 全流程
python -m cs2_pro_settings update --scheduled  # 定时源 live 流程
python scripts/render_accepted.py            # 重新生成已接受的月度报告
```

## 仓库结构

```
src/cs2_pro_settings/    v2 管线（identity、cohort、roster、metrics、drift、
                         report、plots、sources、...）
config/                  cohort.yaml、sources.yaml、conclusions.yaml、
                         stability.yaml、team-mappings.yaml、rankings/
data/aggregate/          已接受快照（2026-05.json、2026-08.json、latest.json）
reports/                 确定性双语报告（latest.*、YYYY-MM.*；
                         2026-05.md = 保留的历史遗留报告）
figures/                 确定性 headline 图
social/                  人工/编辑出版档案（自动化永不修改）+ 出版记录
scripts/                 actions_*.py（自动化）、render_accepted.py
tests/                   离线测试 + fixtures
```

## 历史 2026-05 分析

`reports/2026-05.md` 是最初的深度分析（41 支战队 / 198 名选手，快照 2026-05-05）。它是对单一快照的、带时间标记的描述性分析，原样保留；标准化双语报告自 2026-08 起。

## 许可

- 源码：MIT（`LICENSE`）。
- 报告、文档、生成图：CC BY 4.0（`CONTENT_LICENSE.md`）。
- 第三方源数据：不由本仓库重新许可（`DATA_PROVENANCE.md`）。

## 局限

- 所有统计描述的都是抽样职业选手 cohort；某项设置在职业选手中常见，并不代表它能带来竞技表现提升。
- `valid_n` 逐字段不同；缺失字段永远不会默认使用完整 cohort 作为分母。
- roster 稳定性守卫是运维性质的，设计上偏保守。
- 跨 run 运行时状态（GitHub Actions 缓存）是尽力而为；缓存丢失只会产生安全的 warm-up run，不会产生虚假漂移告警。
- 解释性/结论性文字由人工撰写；管线只产生确定性数据与报告。
