# 2026 年 10 月准星格式迁移与发布准备

本次实现解决新格式字段丢失及跨口径比较问题。正式设置快照仍为 2026-08-11；正式 Core 排名仍为 2026-08-10。本次 10 月 8 日复采是当前已接受范围上的本地候选，尚非 10 月排名范围的新一期。

## 口径

- `legacy-v1`（历史记录未标明格式时按旧口径处理）：旧尺寸单位；颜色模式 0–4 为预设，5 为 Custom。预设模式存储的 RGB 是潜在值，不计为有效颜色。
- `cs2-v1`、过渡的 `legacy-v3` / `legacy-v4`：像素尺寸、直接 RGB。来源名称中的 legacy 不表示旧尺寸单位。完整 RGB 在现有展示类别中记为 Custom，**不表示玩家选择了旧自定义模式**，不伪造模式 5。
- `outlineMode` 0/1/2 分别为无／全／半描边。新格式优先使用该字段；缺失或非法值保持未知，不从布尔值猜测。`legacy-v3` 的来源格式仍用布尔开关，按无／全保存。
- 保存原始格式、分享码、参考 `screenHeight`、T 型开关及逐字段来源；分享码作为本地来源信息保留，不进入公开聚合。
- 尺寸按格式与准星参考高度分别统计。多个上下文时，原有合并尺寸及 Gap × Size 图数据置为空；双语报告呈现分组中位数与各自 `valid_n`。缺失高度／未知格式不生成尺寸中位数，不以视频分辨率推断高度，不做近似换算。
- 聚合增加 `measurement_version`。与历史口径或不同格式集合比较时，只停用准星趋势规则，鼠标和显示规则继续运行。混合格式集合改变也会重新触发基线要求，属于保守策略。

## 10 月 8 日在线复采

运行 CS2Settings 的正常 HTTP 采集，使用当前已接受队伍配置；未启用其他来源。全量抓取覆盖 35 支追踪队伍，核心范围 30 支队伍的名册和 150/150 名成员均成功，无来源失败或名册歧义。采集成功不等于每个人都有设置。

| 指标（Core） | 结果 |
|---|---:|
| 阵容成员 | 150 |
| 有任意设置 | 132 |
| 无设置 | 18 |
| 有效准星颜色 | 132 / 132 有设置者（132 / 150 阵容成员） |
| cs2-v1 / legacy-v4 / legacy-v1 | 89 / 27 / 16 |
| 直接 RGB + 旧 Custom，三通道完整 | 123 / 123 |
| 无／全／半描边 | 121 / 10 / 1（n=132） |
| 无点且无描边 | 84.85%（n=132） |

同一批采集数据中，保留旧颜色模式字段的仅 16 人；新增格式路径使 116 人的直接 RGB 得到解释。PR #17 的 18/133 是另一日期的采集，不能当作本次同样本前后对比。132/132 的覆盖率是适配验证，不代表新颜色趋势已经成立。旧预设与新直接 RGB 即便视觉颜色相同，仍分别呈现，避免把新 RGB 集中归为 Custom 的现象解读成偏好变化。

参考高度有明显差异。例如抽查中 ZywOo 的准星高度为 768，页面显示分辨率为 1280×960。混合尺寸不能计算一个总体中位数。

本地 `work/` 中保存了 collection-manifest、observations、metrics 及双语 candidate report；未提交来源原始数据或接受新快照。

## 10 月 5 日排名候选

新增 `config/rankings/valve/2026-10-05.yaml`，来自 Valve 官方公开文件；仅导入队名和名次，不把官方排名中的名单当作当前阵容。

- 进入 Top 30：Nemiga、Luminosity、3DMAX、M80、100 Thieves、Nemesis、JiJieHao。
- 离开 Top 30：Natus Vincere、PARIVISION、The MongolZ、TYLOO、Dendele、HOTU、EYEBALLERS。
- Nemiga、Nemesis、JiJieHao 缺少现有队伍映射，候选明确标为 unresolved；另外四支新入围队伍已有映射，但本次旧 Core 的完整采集不能代替新 Core 的覆盖审核。

## 待讨论与后续工作

1. 审核新队伍身份和来源映射，确认离开 Core 队伍是否进入 watchlist，再激活 10 月排名并按新范围复采。
2. 选择新准星正式基线。暂停 #14 中旧口径的“无点无描边”和颜色趋势解释；不要直接发布 #17 的旧适配结果。
3. ProCrosshairs 可以提供带时间戳的准星核验，但来源政策、完整覆盖、分享码解码和同源关系仍需单独核查，本 PR 未启用该来源。
4. 当前页面对象未暴露完整的描边颜色／瞄准镜字段，本 PR 保存分享码但不新增解码器；后续应审计编码版本后再纳入这些字段。
5. 跨格式视觉颜色是否需要统一色系分类，以及尺寸是否要换算到统一参考高度，应另定有依据的规则；本次先保留精确 RGB 和尺寸上下文。

## 来源与验证

- [Valve 9 月 23 日更新](https://steamcommunity.com/games/CSGO/announcements/detail/1844751498216924)
- [Valve 9 月 24 日说明](https://steamcommunity.com/games/CSGO/announcements/detail/1844751498219795)
- [Valve 10 月 1 日更新](https://steamcommunity.com/games/CSGO/announcements/detail/1845383656379136)
- [CS2Settings donk](https://cs2settings.com/players/donk)、[ZywOo](https://cs2settings.com/players/zywoo)
- CS2Settings 2026-10-08 页面所引用的 `_app/immutable/chunks/C8I7bjgv.js`：格式转换、像素格式判断、`None/Full/Half` 标签及直接 RGB 语义核对；只记录结论，不提交第三方脚本。
- [官方 VRS 2026-10-05](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md)

回归测试覆盖新旧颜色语义、过渡格式、非法／缺失 RGB、描边优先级、参考高度隔离、逐字段来源、双语报告及迁移期间的趋势抑制；使用合成样本。CI 仍为离线 pytest、离线端到端及 run2/run3 确定性比较。
