# X Content Research & Growth Engine

面向单人中文 X 创作者的本地研究工作台。目标是把真实帖子发现、对照研究、独立素材、人工创作与发布后反馈连成可复查的闭环。当前已有来源记录、人工录入和研究资料包，但可比较样本仍为零；没有经过验证的“爆款公式”。

## 运行

需要 Python 3.10+，不需要 API 密钥或额外付费依赖。

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

默认数据库为 `data/research.sqlite3`（不提交 Git）；`--db 路径` 可指定位置。`capture` 只监听本机 `127.0.0.1`，打开 [本地录入页](http://127.0.0.1:8765/) 后，研究人员在 X 正常界面人工查看原帖，再填入链接、短摘录、证据和可见指标。批量数据可用 `import-csv 文件.csv`；表头至少包含 `url,author_handle,topic,excerpt,observed_at,source_url,evidence_note`，确认原帖时另需 `verification_status=ORIGINAL_CONFIRMED,human_checked=true,evidence_ref`。时间必须为 UTC ISO 格式；`metric_as_of` 是指标所属时间，不能拿搜索时刻代替。CSV/JSON 导入按帖子 ID 和完整观察指纹去重，冲突值并存以供审查。截图和个人数据应放在被忽略的 `data/private/` 或 `data/evidence/`。

种子文件是版本化的公开搜索索引观察，指标可能过时；缺失数值用 `null`。当前 11 个不同 X URL 中只有 1 个做过原帖摘要核对，7 个有可入数值字段的索引浏览量（3 个精确显示、4 个缩写近似），另 4 个仅有缩写或无浏览量，0 个有可靠的定时非索引指标，0 组可比较对照。请先读 [Browser Harness 权限边界](docs/BROWSER_RESEARCH_POLICY.md) 和 [查询实测](docs/QUERY_PROBE_2026-09-29.md)。本项目不自动控制 X 网页、读取 Cookie 或绕过访问限制。

当前工作顺序和断点见 [TASK_STATE.md](TASK_STATE.md)；研究规范、参考项目证据和架构决策见 `docs/`。任务用 GitHub Issues 跟踪，实际数据与结论以仓库版本为准。

`research-packet` 把实际 X 链接、指标来源、质量缺口、对照关系、结构标注和待验证假设导出为 Markdown/JSON，供人工交给当前 ChatGPT 会话，不调用模型 API。经人工审查的研究输出可用 `import-review` 以 `HYPOTHESIS` 状态留存版本；结构标注和配对分别用 `import-annotations`、`import-pairs`，READY 配对有质量门槛。三篇不同题材的原创候选在 [审核文件](docs/ORIGINAL_DRAFTS_2026-09-30.md)，未发布。真实发布后才可用 `import-feedback feedback.json` 录入本人账号结果，必须包含 `human_reviewed: true`。项目不附伪造反馈，也不连接 X 账号。

公开仓库使用标准 GitHub Actions runner 执行同一条本地单元测试命令；[GitHub 文档](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)说明标准 runner 对公开仓库免费。CI 不运行网络采集，不上传附件。

2026-10-01 首批发布候选见 [8 条短帖及核对说明](docs/PUBLICATION_BATCH_2026-10-01.md)，机器记录为 `data/publication_batch_2026-10-01.json`。其中三条重写旧稿，五条为新增；后续经用户明确指定 Computer Use，两轮八条均已发布并核对原帖。独立素材可回放总数为七条。账号专属截图与初始指标保存在 ignored local 路径；这些代理观察未作为人工审核反馈导入，种子回放的 own_posts 仍为零。发布授权无需重复索取。

后续按用户要求停止凭“幽默”继续扩量，新增 [开源爆帖研究与实验设计](docs/VIRALITY_RESEARCH_OPEN_SOURCE.md)。`phase2_materials_round5.json` 保存四条方法/研究来源，完整回放素材总数为十一条；这些不是 X 样本或已验证公式。人话版测试批实际发布九条、三条未发布，记录见 `data/publication_batch_2026-10-01_human.json`。以后以固定观察窗口、作者/时间 holdout、普通对照和反例进行研究，再安排原创测试。

进一步核验了 8 个公开仓库的锁定版本、10 条 Reddit/LINUX DO 方法线索（7 条原页、3 条原页失败的索引线索）；登记表为 `data/virality_method_registry_2026-10-01.json`。加入 round6 后完整回放素材为 15 条，外部 X 证据仍为 11 链接/13 观察、0 组 READY 对照。基于当前 X 公开源码的[纠错测试帖](docs/SOURCE_LED_PUBLICATION_2026-10-01.md)已发布，账号总计 18 条代理核验发布；这不是已验证的传播效果。旧 30 条夜间文案已退出当前队列。三项下一轮比较机制记录在 `data/next_publication_experiment_2026-10-01.json`，状态为计划，尚非完成的实验。

## Direct visible research and source-led publication — 2026-10-01

[32 posts above 10,000 views and five structural hypotheses](docs/VIRAL_SAMPLES_AND_FORMULAS_2026-10-01.md) records actual local Browser Harness observations, 29 authors, 12 detail visits and 10 lower-view nonreply comparisons. These comparisons have unmatched ages; no causal pairs or validated formula. Raw metric labels, UTC and agent-only verification are preserved in `data/viral_samples_2026-10-01.json`. Screenshots and raw texts remain private. This separate research batch does not silently promote the SQLite human-confirmation workflow.

[Four further source-led originals](docs/SOURCE_LED_PUBLICATION_2026-10-01_BATCH2.md) were published and individually verified: behavioral research, a local file-transfer tool, an official policy document and a NASA experiment. Account publications total 22; growth effects remain unknown.

[Second-stage comparison research](docs/VIRAL_VALIDATION_STAGE2_2026-10-01.md) adds 208 unique observed links from 74 authors, including 89 above 10,000 views and 28 structural reviews. Mature counterexamples, near-duplicate content and a predictor claim audit are retained. None of the 78 coarse pair candidates meets the full matching requirements; no formula is promoted. Two source-checked candidates remain unpublished because the user's research-before-publication confidence gate is unmet. A local current-chat continuation checks evidence every two hours; further publication requires a documented editorial judgment and sufficient evidence.

The subsequent user instruction permits gradual publication tests while research continues. [Public-figure contrast research and three new originals](docs/PUBLIC_FIGURE_CONTRAST_2026-10-01.md) records 27 further observed links, five structural reviews, four detail visits and a new unpromoted hypothesis. R06–R08 are now individually verified; account publication count is 25. The local continuation publishes 1–2 eligible originals per run, without claiming the earlier high-confidence virality gate was achieved.

The active 200-post campaign has since verified 17 additional originals through visible Chrome UI, bringing the agent-verified account total to 42. Fourteen of the campaign's first batch were expanded with source checks and C017 cites the [Nobel Physics 1921 record](https://www.nobelprize.org/prizes/physics/1921/summary/). The campaign still has 183 research-pending briefs; this work-item count is not a publication count, and no reach or virality outcome is claimed.

The campaign then verified C019 and C020 as two further originals, bringing the agent-verified total to 44. C019 uses the [Nobel 2015 medicine summary](https://www.nobelprize.org/prizes/medicine/2015/summary/) and C020 uses the [NASA Challenger commission report](https://www.nasa.gov/history/rogersrep/v1ch3.htm). The queue now has 181 research-pending briefs; this is not a reach or virality result.

C021 adds an explicitly labeled “暴论” writing hypothesis about recitable wording and evidence. It is recorded as editorial material, not as a viral formula or empirical finding; the agent-verified account total is now 45 and 180 campaign briefs remain research-pending. The next editorial scope includes medium-known creators, entertainers, streamers, entrepreneurs and controversial public figures.

**Publication-quality correction:** C019–C021 initially lost Chinese text during input and were wrongly marked verified from send confirmations. They have now been repaired, independently reloaded and compared with clean drafts; final/old version URLs are preserved in the campaign manifest. Edits do not increase the publication count. The latest user target is 1000 additional distinct original series; the existing 20 campaign series count toward it. A later Computer Use paste timed out and keyboard input again dropped Chinese, so no post was submitted; the malformed draft was cleared. Resume with [user decisions](docs/USER_DECISION_LOG.md), [根哥 voice and publication checks](docs/CONTENT_VOICE_AND_WORKFLOW.md), and both task-state files. No dedicated continuous account-flow monitoring is required; relevant natural replies are authorized, manufactured engagement is excluded.

C201 through C206 have passed the recovered visible-editor input path and independent public-detail verification. Current counts are 26 published, 0 ready, 180 research-pending; the rolling queue has 206 items while the long-term goal is 1000 additional originals.
