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
- `primary_action`: 且仅且一个：`SHARE`、`REPLY`、`QUOTE`、`FOLLOW`、`DWELL`、`SAVE_RETURN`、`CLICK_RESOURCE`。
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


## 2026-10-08 新读者模型契约

候选新增必填reader_model，见SELF_MIRRORING_RESEARCH_2026-10-08.md和growth_engine/reader_model.py。必须分别记录材料强度、题材强度、具体心理筹码、自我映射/八项distance及bridge、预期违背、场景、信息差、表达入口、真实观点空间、具体转发对象、内心第一句、覆盖证据与风险。标签HIGH/MEDIUM/LOW为编辑序数，UNKNOWN保持未知；心理预测不得标成实测。

reader-review输出A–I弱项与REVIEW_FIRST/LOWER_PRIORITY/HOLD_NEEDS_ANNOTATION，不给总分。每项极弱降低优先级；候选缺模型/筹码/内心回应/转发对象或理由、材料/自我映射/筹码LOW或UNKNOWN、摘要证据、RESEARCH_ONLY机制、重复材料、被动“哦/知道了/挺有道理”不能过闸门。REPLY还需表达入口，SHARE还需转发价值；不能用CTA替代。强资源可以没有强反转，仍需陈述弱项与单一动作，不把乘法当硬性必需因果。FAIL/HOLD/RESEARCH_ONLY状态不能形式过闸门。已发布历史只回顾，不改稿或重新发布。
