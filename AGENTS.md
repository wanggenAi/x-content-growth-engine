# Long-term development constraints

- On every resumed session or new machine, first read `docs/CONTENT_VOICE_AND_WORKFLOW.md`, `docs/USER_DECISION_LOG.md`, `TASK_STATE.md` and `state/task_state.json`. Persist every substantive user steer, decision, failure and real output before ending a work round. Preserve latest wording and post-version checks; send confirmation alone never qualifies a post as verified.

- This repository is independent. Do not modify other repositories or purchase services.
- Zero incremental cost: no paid X/API/model calls, proxy, cloud resource or subscription. Confirm free access before adding any integration.
- Never install or run third-party tools that read browser cookies, access social accounts, or automate pages without a separate safety, permission and platform-policy review.
- Preserve original post links, observation source, UTC capture time and missing values. Never invent posts, metrics, authors, experience or outcomes.
- Keep search-index observations distinct from direct X observations and user-provided records. Search results are discovery leads, not an unbiased sample or a live metrics feed.
- Browser Harness may test local UI and permitted non-X sources. It does not authorize automated X browsing, scraping or account actions; apply the recorded permission gate in `docs/BROWSER_RESEARCH_POLICY.md` before changing that boundary.
- Never mark a manually supplied original as confirmed without `human_checked`, a source reference and a note. Keep approximate indexed metrics nonnumeric when their precision is unknown.
- Public repository: keep screenshots, Cookie files, personal account analytics, tokens and private research notes under ignored local paths; commit only safe public links and summaries.
- Keep X research samples, internet source material, formula hypotheses and own publication results in distinct tables and workflows.
- Formula states are HYPOTHESIS, REPLICATED, EXPERIMENT_SUPPORTED, REJECTED and REVIEW_REQUIRED. Code must not promote a formula by an arbitrary score.
- Research claims need controls, independent holdout evidence and counterexamples. Topic clusters are not mechanisms; observed mechanisms are not tested outcomes.
- Reddit data requires verified authorization and use rights before bulk collection, model training or production dependency. Prefer independently authorized sources.
- Human review and manual X publishing are required. Do not impersonate the user or manufacture engagement.
- Update `TASK_STATE.md` and `state/task_state.json` at each checkpoint; commit evidence, tests and decisions. Keep the SQLite runtime database out of Git and preserve reproducible seed/evidence records.
- Prefer Python standard library and SQLite until measured needs justify dependencies. Run tests and audit before claiming a milestone.

## Editorial-growth control (2026-10-06)

- The canonical gate is `docs/EDITORIAL_GATE.md`; no candidate is READY without subject value, information gap, payload, exactly one primary action, novelty, audit-language separation, follow reason, strong material and provenance fields.
- The primary goal is long-term natural exposure, meaningful interactions and follows. The old 1000-publication target and `remaining_new_publications` are historical inventory/output observations only, never control variables or success metrics.
- Research, material selection, editorial review, manual publication experiments and feedback learning are separate states. A five-minute heartbeat may research or prepare review, but it must never auto-submit a main post.
- Publication is paused in `PUBLICATION_PAUSED_FOR_LEARNING` until the new gate and a pre-registered experiment admit a candidate. Preserve all historical URLs and counts; do not resume batch posting in a repair round.
- Own-post feedback uses `docs/FEEDBACK_LEARNING_LOOP.md` fixed windows and null missing values. High-view observations, formula hypotheses, negative examples and account content memory remain distinct; F01-F05 stay `HYPOTHESIS`.


## 2026-10-09T02:24:58.079200Z — 用户恢复持续发布授权（覆盖旧仅反馈限制）

用户直接原话：「为什么不持续发送？？？？ 发新帖子啊 别不发啊」。持续普通公开新帖发布已获授权，旧PUBLICATION_PAUSED_FOR_LEARNING、heartbeat不能提交及只限C359单条的控制不再作为全局阻塞。继续非X公开材料研究、事实核验、强材料筛选、查重、唯一主动作和预注册反馈实验；用户已免除逐条亲自正文审核，代理核验记agent_checked，human_checked不得伪填。内容机器门槛保留，既有校验器要求human_checked导致的形式不READY必须显式记为用户审核豁免，不能假称完全通过或改值伪装。只能用用户自己的Gen @qiluo27808本机原生可见Chrome编辑器逐条核对、一次提交、独立公开详情重载与来源目标核验；结果不明先查原帖，不能盲重发。每轮最多5条，不硬凑，不因反馈缺失停发。其他账号、API/DOM/隐藏请求/Cookie/社交抓取、自动私信/回复/关注/点赞、私密或高影响通信均不在本次普通发帖授权内。质量条件/安全边界继续，F01-F05保持HYPOTHESIS，历史数量只作盘点。自动化x已从PAUSED改ACTIVE，保留5分钟唤醒与失败才提醒，任务改为持续合格选题发布及独立反馈学习。
