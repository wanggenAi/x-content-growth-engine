# Reader Value Routes

本轮把 `SELF_MIRRORING_V1` 的“心理账户”保留为历史可读层，并新增 `READER_VALUE_V2`。V2 问的是“读者为什么觉得这件材料有价值”，而不是把读者相似性当成普遍传播条件。

## 路由

V2 的初始路由是 `SELF_RELEVANCE`、`CURIOSITY`、`EPISTEMIC_REWARD`、`KNOWLEDGE_CORRECTION`、`WONDER`、`UTILITY`、`IDENTITY`、`STATUS`、`COMPARISON`、`EMOTIONAL_RESONANCE`、`OPINION_EXPRESSION`、`SOCIAL_CURRENCY`、`HUMOR_ABSURDITY`、`NARRATIVE_CLOSURE`。词表可扩展，但新路由必须有定义、文字线索和可能的读者内心话。

`SELF_RELEVANCE=LOW/UNKNOWN` 不会单独阻止审核。一个陌生工艺或技术机制可以是低自我相关、高好奇心、高材料强度的候选。`self_relevance`、`curiosity`、`material_strength` 分开记录，不能互相代替，也不能相乘为传播概率。

好奇路由细分为 `KNOWLEDGE_GAP`（不知道答案）、`MECHANISM_CURIOSITY`（想知道如何运作）、`CORRECTION`（常识被真实来源校准）、`NOVELTY`（以前没见过）、`WONDER`（能力或结果超出预期）、`COUNTERINTUITIVE_FACT`（事实违反直觉）、`HIDDEN_PROCESS`（幕后过程）、`RARE_OBJECT`（陌生物件）和 `RARE_SKILL`（陌生职业或罕见能力）。这些是编辑标注类型，不是好奇心量表。

## 共同字段与动作字段

所有候选先填写材料强度、证据覆盖、查重状态、明确的 reader-value route、`why_reader_cares` 和自然的 `predicted_inner_response`。只有相关动作才填写动作字段：

| primary_action | 必需接口 |
| --- | --- |
| `SHARE` / `QUOTE` | `social_currency`、`share_recipient`、`share_reason` |
| `REPLY` | `opinion_activation`、`activation_mechanisms`、`opinion_space` |
| `SAVE_RETURN` | `utility`、`future_usefulness`、`concrete_resource` |
| `CLICK_RESOURCE` | `resource_value`、`source_accessibility`、`actionability` |
| `DWELL` | `curiosity`、`information_gap`、`narrative_progression`、`expectation_violation` |
| `FOLLOW` | `why_follow`、`repeatable_value`、`account_positioning`、`future_expectation` |

`expectation_violation` 可以是 `LOW` 或 `UNKNOWN`；有用的资源不需要强行制造反转。`KNOWLEDGE_CORRECTION` 必须同时记录常见说法、来源支持的修正和来源引用，不能故意写错诱发纠错。

不使用总分、万能公式或自动升级。`review_profile()` 只返回 `REVIEW_FIRST`、`LOWER_PRIORITY` 或 `HOLD_NEEDS_ANNOTATION` 及具体缺口。任何结果都不能把 `HYPOTHESIS` 变成 `REPLICATED` 或 `VERIFIED_ON_OWN_ACCOUNT`。

## 分层深审

`data/reader_value_stratified_sample_2026-10-08.json` 是 28 条审查样本：15 条外部发现、13 条自帖，覆盖全部初始路由和多种动作。外部样本的证据覆盖明确为 `STRUCTURE_SUMMARY_ONLY`，只保留原始公开链接；自帖样本保留公开发布记录。该文件是有限深审，不是把剩余数百条历史注释机械补齐。生成命令是：

```sh
python3 scripts/build_reader_value_sample.py
```

`C355` 在样本中标为发布后的 `CURIOSITY` 回顾；原始 `SHARE` 预注册、正文、链接和窗口记录不被改写，也不为这条历史实验追加新的发布授权。

## 前瞻实验

`data/prospective_reader_value_experiment_2026-10-08.json` 预注册 12 个槽位，分布在：H1“低自我相关但高好奇心”、H2“可比较的具体筹码”、H3“真实解释缺口”。当前状态是 `DESIGNED_NOT_SCHEDULED`，发布仍处于 `PUBLICATION_PAUSED_FOR_LEARNING`，没有虚构候选、排期或批量发布。每个槽位在进入闸门前仍需独立来源、材料、route 字段、查重、审计语言分离和人工授权。

## 反馈边界

固定窗口容差为 1h ±20 分钟、6h ±30 分钟、24h ±60 分钟、72h ±180 分钟、7d ±360 分钟。每条观测保存 `actual_observed_at`、`actual_post_age_minutes`、`target_window` 和 `offset_from_target_minutes`；晚到数据标为 `LATE_EXPLORATORY`，缺失不补造。`distribution_confidence` 与 `content_failure` 分开，后者在没有证据时保持 `UNKNOWN`。动作指标、定性结果、评论正文和 `activation_prediction_match` 也分开保存。

## 本轮结论与下一步

1. V1 把自我映射、心理账户和分享接口过早当成所有候选的共同门槛，因而会错过远距离但有好奇心、纠错、效用或惊奇价值的材料。
2. 当前注意力入口是自我相关、好奇/认识奖励、知识纠正、惊奇、效用、身份、状态/比较、情绪共鸣、意见表达、社交货币、幽默荒诞和叙事收束。
3. 好奇、认识奖励、知识纠正、惊奇、效用、幽默和陌生叙事可以在 `self_relevance=LOW/UNKNOWN` 时成立；是否成立要看材料、证据和对应动作字段。
4. `share_recipient`、`share_reason`、`identity_trigger`、`opinion_space` 已从全局强制字段改为 route/action 条件字段；没有真实依据时不硬凑接收者。
5. 不同 primary action 由不同字段和指标审核，不能用一个 engagement 总分替代：回复看表达入口，分享看社交货币，保存/点击看效用和行动性，停留看好奇/信息差，关注看可重复价值。
6. 下一阶段先从12个已预注册槽位中逐条取材，目标10–20条真实帖子；每条只突出一个主要差异，手工通过闸门后一次发布，再按固定窗口收集动作和评论证据。
7. 优先验证 H1（低自我相关的高好奇心）、H2（可比较的具体筹码）、H3（真实解释缺口），分别使用 DWELL/SAVE/SHARE、REPLY/SHARE、REPLY 等主要动作。
8. 若低自我相关高材料在足龄窗口仍无停留/保存，或比较信息没有动作优势，或解释缺口没有预测中的评论类型，且分发置信度足够高、来源和窗口完整，则对应假设保持或转为 `REJECTED`；低浏览但分发不确定时不能判内容失败。
