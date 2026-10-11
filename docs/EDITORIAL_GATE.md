# Editorial Gate（发布硬闸门）

更新：2026-10-06。该闸门是候选进入 `READY_FOR_MANUAL_PUBLISH` 前的机器可读和人工复核契约。事实核验仍是必要条件，但事实核验通过不等于值得发布。

## 目标与状态

项目最高目标是提高账号长期自然曝光、有效互动和关注增长；发布数量只是输出/观察计数。任何 heartbeat、队列长度或 `remaining_new_publications` 都不能绕过本闸门。

候选状态：

`DISCOVERED` → `SOURCE_CHECKED` → `MATERIAL_STRONG` → `DRAFT` → `EDITORIAL_REVIEW` → `READY_FOR_MANUAL_PUBLISH` → `PUBLISHED_PENDING_FEEDBACK` → `OBSERVATION_CLOSED` → `LEARNING_REVIEWED`

可在任意审核点进入：`FAIL_LOW_INTEREST`、`FAIL_REPETITIVE`、`FAIL_NO_PAYLOAD`、`FAIL_NO_PRIMARY_ACTION`、`HOLD_NEEDS_EVIDENCE` 或 `RESEARCH_ONLY`。`READY_FOR_MANUAL_PUBLISH` 不是自动发布授权；只有独立的人工 publication experiment 才能提交一次。

## 必填 gate record

每条候选必须保存以下字段；字符串须为具体句子，不能用“有道理”“值得讨论”“提高认知”等空话代替：

- `candidate_id`, `research_version`, `publication_version`
- `subject_value`: 至少一个强价值（新鲜事实、利益/金钱、损失/机会/风险、强人物/画面/冲突、强信息增量、可执行资源/步骤、真实猎奇或具体机制）。只有正确观点则失败。
- `information_gap`: 第一行后读者仍不知道的具体未知点；若可猜出全文则失败。
- `payload`: 读者拿走的事实、数字、账、故事、动作、原材料、资源、方法、表达或解释框架；只有“一个观点”则失败。
- `primary_action`: 且仅且一个：`SHARE`、`REPLY`、`QUOTE`、`FOLLOW`、`DWELL`、`SAVE_RETURN`、`CLICK_RESOURCE`、`LIKE`。
- `primary_action_reader`: 哪类读者为什么会做该动作；不能写“所有人”。
- `novelty_check`: 与近 20–30 条自有内容在题材、冲突、首屏、结尾、句式、情绪、关系、价值判断和媒介上的重复结论。
- `audit_language_separation`: 研究版的证据边界、未知值、来源和限制；公开版不得机械复制审计腔。事实边界必须留在研究记录。
- `follow_reason`: 发完后读者为何愿意看下一条；没有理由则失败。
- `material_strength`: `STRONG` 或 `INSUFFICIENT`，并写明素材本身的传播价值；漂亮结构不能把普通材料升级成强材料。
- `source_refs`, `fact_check_status`, `human_checked`: 真实来源和人工状态。未核主张只能 `HOLD_NEEDS_EVIDENCE`。

## 机器规则

`growth_engine.editorial_gate.validate_candidate()` 实施上述必填字段、单一 primary action、允许状态和强度值检查。验证只说明“满足进入人工复核的形式条件”，不预测浏览或关注。失败记录原因，不改词绕过，不占发布数量。

## 研究版与公开版

研究版可以记录“只能确认”“作者自述”“时间未知”“样本有混杂”等边界。公开版用自然人话表达已确认的事实和明确标注的自拟观点；不得伪造经历、把评论当来源、把研究限制抄成免责声明，也不得用审核通过冒充传播结果。

## 人工发布前最后检查

人工在可见原生 X 编辑器逐字核对中文、标点、空行、链接、媒体与一次提交；确认编辑器关闭后，独立公开详情重载核对账号、全文、换行、来源卡片和显示时间。发送提示不是正文核验。没有完成这些步骤，状态不能进入 `PUBLISHED_PENDING_FEEDBACK`。


## 2026-10-08 Reader Value V2 契约

候选仍必须有 `reader_model`，但生产模型是 `READER_VALUE_V2`。共同核心是材料强度、证据覆盖、查重状态、一个或多个明确 reader-value route、`why_reader_cares` 和自然的 `predicted_inner_response`。`SELF_RELEVANCE=LOW/UNKNOWN` 不会单独阻止候选；它与好奇心、效用、知识纠正、惊奇、身份、比较、情绪、意见、社交货币、幽默和叙事收束分开记录。

动作字段按 `primary_action` 条件触发：`SHARE/QUOTE` 需要 `social_currency`、`share_recipient`、`share_reason`；`REPLY` 需要 `opinion_activation`、`activation_mechanisms`、`opinion_space`；`SAVE_RETURN` 需要 `utility`、`future_usefulness`、`concrete_resource`；`CLICK_RESOURCE` 需要 `resource_value`、`source_accessibility`、`actionability`；`DWELL` 需要 `curiosity`、`information_gap`、`narrative_progression`、`expectation_violation`；`FOLLOW` 需要 `why_follow`、`repeatable_value`、`account_positioning`、`future_expectation`。没有相关动作时，不强制无关字段。

`reader-review` 输出具体缺口和 `REVIEW_FIRST`、`LOWER_PRIORITY`、`HOLD_NEEDS_ANNOTATION`，不返回总分。UNKNOWN 保持未知；结构摘要只能留在研究层，`RESEARCH_ONLY` 和重复材料不能进生产。`KNOWLEDGE_CORRECTION` 必须有真实来源支持，不得故意造错诱骗纠错。`predicted_inner_response` 是编辑预测，不是实测心理。已发布历史只回顾，不改稿或重新发布。

已发布、已关闭或已完成学习的历史 `SELF_MIRRORING_V1` 记录保留兼容读取路径，便于审计和反馈回放；它们不代表新候选可以继续用旧模型进入生产。新的 `EDITORIAL_REVIEW` 候选必须通过 `READER_VALUE_V2` 的 route/action 校验。


## 2026-10-09T02:24:58.079200Z — 用户恢复持续发布授权（覆盖旧仅反馈限制）

用户直接原话：「为什么不持续发送？？？？ 发新帖子啊 别不发啊」。持续普通公开新帖发布已获授权，旧PUBLICATION_PAUSED_FOR_LEARNING、heartbeat不能提交及只限C359单条的控制不再作为全局阻塞。继续非X公开材料研究、事实核验、强材料筛选、查重、唯一主动作和预注册反馈实验；用户已免除逐条亲自正文审核，代理核验记agent_checked，human_checked不得伪填。内容机器门槛保留，既有校验器要求human_checked导致的形式不READY必须显式记为用户审核豁免，不能假称完全通过或改值伪装。只能用用户自己的Gen @qiluo27808本机原生可见Chrome编辑器逐条核对、一次提交、独立公开详情重载与来源目标核验；结果不明先查原帖，不能盲重发。每轮最多5条，不硬凑，不因反馈缺失停发。其他账号、API/DOM/隐藏请求/Cookie/社交抓取、自动私信/回复/关注/点赞、私密或高影响通信均不在本次普通发帖授权内。质量条件/安全边界继续，F01-F05保持HYPOTHESIS，历史数量只作盘点。自动化x已从PAUSED改ACTIVE，保留5分钟唤醒与失败才提醒，任务改为持续合格选题发布及独立反馈学习。
