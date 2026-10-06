# Review Packet — 2026-10-06

供用户与 ChatGPT 审核。此轮完成结构修复后停止批量发布；历史记录和未知值保留。

## A. 原系统问题

`active_1000_further_publication_campaign`、`remaining_new_publications` 和五分钟 heartbeat 让队列/发布数变成实际控制变量。事实核验与传播价值、研究与公开文案、发布成功与学习结果混在一起；own-post 没有统一成熟窗口，重复结构和低价值素材缺少硬失败路径。

## B. 本次修改

新增 [EDITORIAL_GATE](EDITORIAL_GATE.md)、[EXPERIMENT_PROTOCOL](EXPERIMENT_PROTOCOL.md)、[FEEDBACK_LEARNING_LOOP](FEEDBACK_LEARNING_LOOP.md)、[X_ALGORITHM_STRATEGY](X_ALGORITHM_STRATEGY_2026-10-06.md)、[CONTENT_MEMORY](CONTENT_MEMORY.md)，并加入可运行的 `growth_engine.editorial_gate` 校验与 CLI `editorial-gate`。新增 30 条学习实验设计 JSON；更新 AGENTS、README、workflow、TASK_STATE、state JSON 与 campaign 元数据。

## C. 废除的错误目标

1000 条不再是必须完成的发布 KPI；剩余 843 不再决定下一动作；队列不再自动填满；heartbeat 不再默认发帖；发送成功不再等于项目成功；F01–F05 不升级。

## D. 新最高层目标

提高账号长期自然曝光、有效互动和关注增长。次级目标是找出适配内容类型、建立高质量素材库、可证伪假设、可重复创作流程、真实反馈闭环并持续淘汰低价值模式。数量仅作输出/观察计数。

## E. Editorial Gate

候选必须通过 subject value、information gap、payload、唯一 primary action、novelty、audit-language separation、follow reason、material strength、来源与人工状态。只有 `READY_FOR_MANUAL_PUBLISH` 才能进入人工实验审查。

## F. 状态机

`DISCOVERED → SOURCE_CHECKED → MATERIAL_STRONG → DRAFT → EDITORIAL_REVIEW → READY_FOR_MANUAL_PUBLISH → PUBLISHED_PENDING_FEEDBACK → OBSERVATION_CLOSED → LEARNING_REVIEWED`；可转 `FAIL_LOW_INTEREST`、`FAIL_REPETITIVE`、`FAIL_NO_PAYLOAD`、`FAIL_NO_PRIMARY_ACTION`、`HOLD_NEEDS_EVIDENCE`、`RESEARCH_ONLY`。

## G. 发布为何暂停

当前没有成熟统一反馈窗口，ready=0；C353 之后的素材还未通过新闸门。用户已明确要求开始发布，因此只允许在候选通过新闸门、预注册 LE30 首条试验并完成可见编辑器人工复核后启动一条；不批量启动 C354。

## H. 下一阶段研究

先完成高/普通/低样本和自身历史 corpus 的素材强度、分发混杂、内容记忆与负例标注；再从强素材中预注册最多 30 条学习实验候选。重新检查 X 官方推荐资料时只记录事实、推断和实验假设。

## I. 绝对禁止

不因剩余数或 heartbeat 自动发帖；不把 indexed views 当实时指标；不把评论当来源；不改词绕过重复拦截；不编造缺失反馈、作者经历、算法权重或因果；不把 agent_checked 冒充 human_checked；不批量抓取 Reddit、Cookie 或隐藏接口。

## J. 仍无证据

没有可用的本账号统一 1h/6h/24h/72h/7d 反馈样本；没有有效因果对照或已验证公式；X 线上排名权重、临时开关、账号规模校正未知；高浏览观察不能证明机制。

## K. 待用户与 ChatGPT 决策

1. 选择第一批强素材和唯一 primary action；2. 确认本人可见 analytics 的合法来源与人工核对方式；3. 选择实验单元与停止条件；4. 何时把某候选从 review 放入人工 publication experiment；5. 如何在不泄露私人截图的前提下复核反馈。
