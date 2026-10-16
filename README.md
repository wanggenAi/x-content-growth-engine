# X Content Research & Growth Engine

> **Current control state:** read [`docs/CURRENT_CONTROL_STATE.md`](docs/CURRENT_CONTROL_STATE.md) first. Historical `PUBLICATION_PAUSED_FOR_LEARNING` checkpoints in older research notes are not the current global state.

面向单人中文 X 创作者的研究与内容增长工作台。目标不是堆发布数量，而是把**新鲜爆帖/普通帖发现 → 结构与反例研究 → 强素材筛选 → 原创写作 → 发布核验 → 真实反馈学习**连成可复查的闭环，在不伪造指标、不制造互动的前提下提高自然曝光、有效互动和关注增长。

## 当前生产状态

- canonical branch：`main`
- PR #5 / `feature/x-research-phase2` 已于 2026-10-11 squash merge 回 `main`
- 当前发布状态：`PUBLICATION_ACTIVE_WITH_QUALITY_GATES`
- 历史 1000 帖目标、queue 数和 publication count 只作盘点，不是成功 KPI
- 没有经过验证的“爆款公式”；高浏览结构、读者心理和自我映射机制仍按证据等级管理
- 事实性内容继续要求来源核验、去重、内容门槛和真实发布后的独立详情页核对

完整控制规则见 [`docs/CURRENT_CONTROL_STATE.md`](docs/CURRENT_CONTROL_STATE.md)。

## 新鲜爆帖数据链

采集与分析分开，避免一边找素材一边把少量样本直接总结成“公式”。详细契约见 [`docs/VIRAL_FEED_CONTRACT.md`](docs/VIRAL_FEED_CONTRACT.md)。

### 1. Viral feed collection

定时任务约每 4 小时运行一次，优先发现最近 48 小时内的公开 X 高传播候选，并允许少量有长期新奇价值的 `EVERGREEN_REDISCOVERY`。

预期输出：

- `data/viral_feed/YYYY-MM-DD/HHMM.json`
- `data/viral_feed/latest.json`
- `data/viral_feed/index.json`
- schema：`data/viral_feed/schema.json`

采集层只负责公开发现、证据规范化、去重和 freshness 标记，不生成帖子、不自动发布、不升级爆款公式。未知指标保持 `null`；零产出也记录查询和失败原因，不拿陈旧数据冒充新数据。

### 2. Viral structure analysis

单独的日任务读取近期 feed，分析高传播样本与可获得的普通/低传播对照。

预期输出：

- `data/viral_analysis/YYYY-MM-DD.json`
- `data/viral_analysis/latest.json`
- `docs/VIRAL_PATTERN_LATEST.md`
- schema：`data/viral_analysis/schema.json`

重点研究首句钩子、信息差、反转、具体数字/人物、自我映射、心理筹码、观点空间、转发对象、叙事节奏、媒体形态、时效性和题材。无法控制作者规模、帖子年龄或题材差异时必须保留 confounder，不把浏览量差异直接解释成因果机制。

## 本地研究工作台

需要 Python 3.10+。核心功能不要求模型 API。

```sh
python3 -m growth_engine init
python3 -m growth_engine import data/seed_x_observations.json
python3 -m growth_engine import data/direct_page_probe.json
python3 -m growth_engine import data/phase2_x_candidates.json
python3 -m growth_engine import data/phase2_x_candidates_round2.json
python3 -m growth_engine import-queries data/phase2_queries.json
python3 -m growth_engine import-queries data/phase2_queries_round2.json
python3 -m growth_engine import-materials data/seed_materials.json
python3 -m growth_engine import-materials data/phase2_materials.json
python3 -m growth_engine import-materials data/phase2_materials_round3.json
python3 -m growth_engine import-materials data/phase2_materials_round4.json
python3 -m growth_engine import-materials data/phase2_materials_round5.json
python3 -m growth_engine import-materials data/phase2_materials_round6.json
python3 -m growth_engine report
python3 -m growth_engine audit
python3 -m growth_engine research-packet --format markdown
python3 -m growth_engine research-packet --format json
python3 -m growth_engine capture --port 8765
python3 -m unittest discover -s tests -v
```

新候选的中文生产链包含 `HUMAN_VOICE_V1`：事实锁定 → deterministic AI Flavor → 保守 Human Voice rewrite → Fact Preservation → X Native Style → Comment Impulse → Editorial Gate。它只在需要时改写，保护数字、日期、实体、链接和原话；高 AI flavor、事实漂移、微型议论文式 X 文本和 REPLY 的 obvious-answer 问题会被挡在 `READY_FOR_MANUAL_PUBLISH` 之前。实现与回放说明见 [`docs/HUMAN_VOICE_PIPELINE.md`](docs/HUMAN_VOICE_PIPELINE.md)。

默认数据库为 `data/research.sqlite3`（不提交 Git）。本地 `capture` 只监听 `127.0.0.1`，用于人工核对公开原帖后的结构化录入。CSV/JSON 导入按帖子 ID 和完整观察指纹去重，冲突值并存供审查。截图和账号专属信息应保留在 ignored 路径，如 `data/private/` / `data/evidence/`。

## 证据纪律

- 公开搜索索引快照不能冒充实时 X 指标
- 缺失数据保持 `null` / `UNKNOWN`
- 原帖、搜索摘要、人工核对和代理核对要区分来源
- promotion / quote / reply / repost 等暴露机制要分层
- 高浏览样本必须配合普通/低浏览反例研究，不能只看赢家
- 外部爆帖只能形成候选机制，不能证明用户账号会复现
- 自己账号的可靠固定窗口反馈优先级更高；历史缺失窗口不能拿当前累计数字倒填

Browser Harness / Computer Use 的权限边界与历史授权记录见 [`docs/BROWSER_RESEARCH_POLICY.md`](docs/BROWSER_RESEARCH_POLICY.md)。不得读取 Cookie、调用隐藏接口、绕过访问控制或制造批量互动。

## 已有研究资产

仓库已保留以下主要研究资产供后续回放，而不是在 README 中继续堆历史状态：

- `docs/VIRAL_SAMPLES_AND_FORMULAS_2026-10-01.md`
- `docs/VIRAL_VALIDATION_STAGE2_2026-10-01.md`
- `docs/HIGH_VIEW_STRUCTURE_*.md`
- `docs/CHINESE_READER_INTEREST_RESEARCH_2026-10-07.md`
- `docs/SELF_MIRRORING_RESEARCH_2026-10-08.md`
- `docs/CONTENT_MEMORY.md`
- `docs/EDITORIAL_GATE.md`
- `docs/FEEDBACK_LEARNING_LOOP.md`
- `data/viral_samples_2026-10-01.json`
- `data/viral_validation_stage2_2026-10-01.json`
- `data/reader_model_annotations_2026-10-08.json`

历史发布、候选、研究回执和计数继续保存在 `TASK_STATE.md`、`state/task_state.json` 与版本化 data/docs 文件中；这些历史记录不应覆盖 `docs/CURRENT_CONTROL_STATE.md` 的当前控制语义。

## 当前工作顺序

1. 持续积累 fresh viral feed，而不是重复消费旧爆帖。
2. 每天形成高传播 vs 普通/低传播对照分析，并主动找反例。
3. 用最新强材料和当前仍有效的结构假设写候选，而不是套固定模板。
4. 只发布通过质量门槛、与近期内容明显不同的稿子，不为数量硬凑。
5. 有可靠反馈时记录真实结果，用失败帖淘汰错误假设。
6. 少加新理论，多做数据、反例和真实账号验证。

CI 使用 `.github/workflows/tests.yml` 在 push / pull_request 时运行标准库单元测试；CI 不负责网络采集。
